function getChromePath() {
    const defaultPaths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        process.env.LOCALAPPDATA + '\\Google\\Chrome\\Application\\chrome.exe'
    ];

    // Primero intentar con las rutas predeterminadas
    for (const chromePath of defaultPaths) {
        if (fs.existsSync(chromePath)) {
            return chromePath;
        }
    }

    // Fallback para webdriver-manager portable
    try {
        // Ruta relativa al webdriver-manager incluido en el paquete
        const webdriverPath = path.join(__dirname, '..', 'node', 'node_modules', 'webdriver-manager');
        const { getInstalledChromePath } = require(webdriverPath);
        
        const chromePath = getInstalledChromePath();
        if (chromePath && fs.existsSync(chromePath)) {
            console.log('Chrome encontrado via webdriver-manager portable:', chromePath);
            return chromePath;
        }
    } catch (e) {
        console.warn('Error al usar webdriver-manager portable:', e.message);
    }

    throw new Error('Chrome no encontrado. Instala Chrome o verifica la ruta manualmente.');
}

const fs = require('fs');
const path = require('path');
const { Writable } = require('stream');
const { Worker } = require('worker_threads');
const puppeteer = require(path.join(__dirname, '..', 'node', 'node_modules', 'puppeteer'));
const targetUrl = process.argv[3] || 'https://www.google.com';

// Worker para escritura asíncrona en hilo separado
const createFileWorker = (outputPath) => {
    const workerCode = `
    const { parentPort } = require('worker_threads');
    const fs = require('fs');
    
    let writeStream = null;
    let isReady = false;
    
    parentPort.on('message', ({ type, data, outputPath }) => {
        if (type === 'init') {
            const dir = require('path').dirname(outputPath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            
            writeStream = fs.createWriteStream(outputPath, { 
                encoding: 'utf8',
                highWaterMark: 128 * 1024
            });
            
            writeStream.on('ready', () => {
                isReady = true;
                parentPort.postMessage({ type: 'ready' });
            });
            
            writeStream.on('error', (err) => {
                parentPort.postMessage({ type: 'error', error: err.message });
            });
        }
        
        if (type === 'write' && isReady) {
            writeStream.write(data);
            parentPort.postMessage({ type: 'written' });
        }
        
        if (type === 'close' && writeStream) {
            writeStream.end(() => {
                parentPort.postMessage({ type: 'closed' });
                process.exit(0);
            });
        }
    });
    `;
    
    return new Worker(workerCode, { eval: true });
};

class ActionRecorder extends Writable {
    constructor(outputPath) {
        super({ objectMode: true });
        this.outputPath = outputPath;
        /** Ruta JSON opcional con metadatos por acción (xpath, selector) para IA / Page Objects */
        this.metaPath = outputPath.replace(/\.js$/i, '') + '_elia_meta.json';
        this.metaRecords = [];
        this.headerWritten = false;
        this.pendingActions = [];
        this.lastInputAction = null;
        this.inputTimeout = null;
        
        // Sistema de escritura optimizado para alta carga
        this.writeBuffer = [];
        this.writeQueue = [];
        this.isWriting = false;
        this.maxBufferSize = 100; // Aumentado para sesiones largas
        this.flushInterval = 500; // Intervalos más largos
        this.batchFlushTimeout = null;
        this.actionCounter = 0;
        
        // Worker para escritura asíncrona
        this.fileWorker = createFileWorker(outputPath);
        this.workerReady = false;
        
        this.fileWorker.on('message', ({ type, error }) => {
            if (type === 'ready') {
                this.workerReady = true;
            } else if (type === 'error') {
                console.error('Worker error:', error);
            } else if (type === 'written') {
                this.isWriting = false;
                this._processWriteQueue();
            } else if (type === 'closed') {
                console.log(`FILE_SAVED:${this.outputPath}`);
            }
        });
        
        // Inicializar worker
        this.fileWorker.postMessage({ type: 'init', outputPath });
    }

    _construct(callback) {
        // El worker maneja la creación del archivo
        callback();
    }

    _write(action, encoding, callback) {
        this.actionCounter++;

        let line = action;
        if (typeof action === 'object' && action !== null && action.line) {
            if (action.meta) {
                this.metaRecords.push(action.meta);
            }
            line = action.line;
        }

        if (!this.headerWritten) {
            const header = `/* URL: ${initialUrl} */\n` + 
                `const puppeteer = require('puppeteer');\n\n` +
                `(async () => {\n` +
                `  const browser = await puppeteer.launch({ headless: false });\n` +
                `  const page = await browser.newPage();\n` +
                `  await page.goto('${initialUrl}');\n\n`;
                
            this._enqueueWrite(header);
            this.headerWritten = true;
        }

        this._processAction(line, callback);
    }

    _processAction(action, callback) {
        if (action.startsWith('await page.type(')) {
            const currentSelector = action.split("'")[1];
            const currentValue = action.split("'")[3];
            
            if (this.lastInputAction && currentSelector === this.lastInputAction.selector) {
                function normalizeValue(value) {
                    return value.replace(/[^a-zA-Z0-9]/g, '');
                }
                
                const normalizedCurrent = normalizeValue(currentValue);
                const normalizedLast = normalizeValue(this.lastInputAction.value);
                
                if (normalizedCurrent.startsWith(normalizedLast) || normalizedLast.startsWith(normalizedCurrent)) {
                    this.lastInputAction.action = action;
                    this.lastInputAction.value = currentValue;
                    clearTimeout(this.inputTimeout);
                    
                    this.inputTimeout = setTimeout(() => this._flushPendingActions(), 2000);
                    callback();
                    return;
                } else {
                    this._flushPendingActions();
                    this.lastInputAction = { 
                        selector: currentSelector, 
                        action: action,
                        value: currentValue
                    };
                }
            } else {
                this._flushPendingActions();
                this.lastInputAction = { 
                    selector: currentSelector, 
                    action: action,
                    value: currentValue
                };
            }
            
            this.inputTimeout = setTimeout(() => this._flushPendingActions(), 2000);
        } else {
            this._flushPendingActions();
            this.pendingActions.push(action);
        }
        
        // Aumentar umbral para sesiones largas
        if (this.pendingActions.length >= Math.min(50, this.maxBufferSize)) {
            this._flushPendingActions(true);
        }
        
        callback();
    }

    _enqueueWrite(data) {
        if (!this.workerReady) {
            this.writeQueue.push(data);
            return;
        }
        
        if (this.isWriting) {
            this.writeQueue.push(data);
        } else {
            this.isWriting = true;
            this.fileWorker.postMessage({ type: 'write', data });
        }
    }
    
    _processWriteQueue() {
        if (this.writeQueue.length > 0 && !this.isWriting) {
            const data = this.writeQueue.shift();
            this.isWriting = true;
            this.fileWorker.postMessage({ type: 'write', data });
        }
    }

    _smartBatchWrite(data) {
        this.writeBuffer.push(data);
        
        clearTimeout(this.batchFlushTimeout);
        
        // Lógica adaptiva basada en carga
        const bufferThreshold = this.actionCounter > 100 ? this.maxBufferSize : 20;
        const flushDelay = this.actionCounter > 100 ? this.flushInterval : 100;
        
        if (this.writeBuffer.length >= bufferThreshold) {
            this._executeBatchWrite();
        } else {
            this.batchFlushTimeout = setTimeout(() => {
                this._executeBatchWrite();
            }, flushDelay);
        }
    }
    
    _executeBatchWrite() {
        if (this.writeBuffer.length === 0) return;
        
        const dataToWrite = this.writeBuffer.join('\n') + '\n';
        this.writeBuffer = [];
        
        this._enqueueWrite(dataToWrite);
        
        clearTimeout(this.batchFlushTimeout);
        this.batchFlushTimeout = null;
    }

    _flushPendingActions(force = false) {
        if (this.lastInputAction) {
            this.pendingActions.push(this.lastInputAction.action);
            this.lastInputAction = null;
        }
        
        if (this.pendingActions.length > 0) {
            this._smartBatchWrite(this.pendingActions.join('\n'));
            this.pendingActions = [];
        }
        
        clearTimeout(this.inputTimeout);
    }

    _final(callback) {
        clearTimeout(this.inputTimeout);
        clearTimeout(this.batchFlushTimeout);

        try {
            const payload = { version: 1, source: 'elia_recorder', actions: this.metaRecords };
            fs.writeFileSync(this.metaPath, JSON.stringify(payload, null, 2), 'utf8');
            console.log('ELIA_META_SAVED:' + this.metaPath);
        } catch (e) {
            console.warn('ELIA meta no guardado:', e.message);
        }
        
        // Escribir datos pendientes en buffer
        this._executeBatchWrite();
        
        if (this.lastInputAction) {
            this.pendingActions.push(this.lastInputAction.action);
            this.lastInputAction = null;
        }
        
        if (this.pendingActions.length > 0) {
            this._enqueueWrite(this.pendingActions.join('\n') + '\n');
            this.pendingActions = [];
        }
        
        // Footer
        const footer = '\n  await browser.close();\n})();\n';
        this._enqueueWrite(footer);
        
        // Esperar a que termine la escritura y cerrar worker
        const checkAndClose = () => {
            if (!this.isWriting && this.writeQueue.length === 0) {
                this.fileWorker.postMessage({ type: 'close' });
                callback();
            } else {
                setTimeout(checkAndClose, 50);
            }
        };
        
        checkAndClose();
    }
}

let initialUrl = '';
let actionRecorder = null;

(async () => {
  try {
    const browser = await puppeteer.launch({
      headless: false,
      defaultViewport: null,
      args: [
        '--start-maximized',
        '--disable-infobars',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--remote-debugging-port=9222',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-extensions',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-background-networking',
        '--disable-sync',
        '--metrics-recording-only',
        '--disable-default-apps'
      ],
      executablePath: getChromePath(),
      ignoreDefaultArgs: ['--enable-automation'],
      timeout: 60000
    });

    const page = await browser.newPage();
    
    await page.evaluateOnNewDocument(() => {
      delete navigator.__proto__.webdriver;
      Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
      });
      Object.defineProperty(navigator, 'languages', {
        get: () => ['es-ES', 'es', 'en-US', 'en'],
      });
      window.navigator.chrome = {
        runtime: {},
      };
    });

    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');

    const outputFile = process.argv[2] || path.join(__dirname, 'grabaciones', 'recorded_actions.js');
    actionRecorder = new ActionRecorder(outputFile);

    // Sistema de cola ultra-optimizado para logAction
    let logActionQueue = [];
    let logActionProcessor = null;
    let isProcessingQueue = false;
    
    const processLogActionQueue = async () => {
        if (isProcessingQueue || logActionQueue.length === 0) return;
        
        isProcessingQueue = true;
        const actionsToProcess = logActionQueue.splice(0, Math.min(50, logActionQueue.length));
        
        // Procesar en chunks para no bloquear
        for (let i = 0; i < actionsToProcess.length; i += 10) {
            const chunk = actionsToProcess.slice(i, i + 10);
            await new Promise(resolve => {
                setImmediate(() => {
                    chunk.forEach(action => {
                        console.log('[Recorded]', action);
                        actionRecorder.write(action);
                    });
                    resolve();
                });
            });
        }
        
        isProcessingQueue = false;
        
        // Procesar cola restante si existe
        if (logActionQueue.length > 0) {
            setImmediate(processLogActionQueue);
        }
    };
    
    await page.exposeFunction('logAction', (action) => {
        logActionQueue.push(action);
        
        if (!logActionProcessor) {
            logActionProcessor = setTimeout(() => {
                logActionProcessor = null;
                processLogActionQueue();
            }, 200); // Delay mayor para sesiones largas
        }
    });

    await page.evaluateOnNewDocument(() => {
      function getXPathForElement(el) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';
        if (el.id) {
          try {
            const sel = '#' + CSS.escape(el.id);
            if (document.querySelectorAll(sel).length === 1) {
              return "//*[@id='" + el.id.replace(/'/g, "\\'") + "']";
            }
          } catch (_) {}
        }

        const parts = [];
        while (el && el.nodeType === Node.ELEMENT_NODE) {
          const tag = el.nodeName.toLowerCase();
          let index = 1, needIndex = false;
          let prev = el.previousSibling;
          while (prev) {
            if (prev.nodeType === Node.ELEMENT_NODE && prev.nodeName.toLowerCase() === tag) {
              index++;
              needIndex = true;
            }
            prev = prev.previousSibling;
          }
          parts.unshift(tag + (needIndex ? '[' + index + ']' : ''));
          el = el.parentElement;
        }
        return '/' + parts.join('/');
      }

      // ── Self-Healing: Fingerprint semántico estable del elemento ──────────────
      function getElementFingerprint(el) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return {};
        const STABLE_ATTRS = [
          'data-testid', 'data-qa', 'data-cy', 'data-test', 'data-id',
          'data-name', 'aria-label', 'aria-labelledby', 'aria-describedby',
          'aria-placeholder', 'aria-controls'
        ];
        const data_attrs = {};
        for (const attr of STABLE_ATTRS) {
          const val = el.getAttribute(attr);
          if (val) data_attrs[attr] = val;
        }
        // Filtrar clases generadas por Angular y frameworks (volátiles)
        const all_classes = (el.className && typeof el.className === 'string')
          ? el.className.trim().split(/\s+/)
          : [];
        const stable_classes = all_classes
          .filter(c => c && !/^ng[A-Z-]|_ng[a-z]|^cdk-|^\d|mat-mdc-/.test(c))
          .slice(0, 5);
        return {
          role:          el.getAttribute('role') || el.tagName.toLowerCase(),
          aria_label:    el.getAttribute('aria-label') || '',
          text_content:  ((el.innerText || el.textContent || '').trim()).slice(0, 80),
          classes_stable: stable_classes,
          data_attrs,
          name_attr:    el.getAttribute('name')        || null,
          type_attr:    el.getAttribute('type')        || null,
          placeholder:  el.getAttribute('placeholder') || null,
          value_attr:   el.getAttribute('value')       || null,
        };
      }

      // ── Self-Healing: Cadena de ancestros semánticos ──────────────────────────
      function getAncestorChain(el, maxDepth) {
        maxDepth = maxDepth || 4;
        const ancestors = [];
        let current = el.parentElement;
        let depth = 0;
        while (current && current !== document.body && current !== document.documentElement && depth < maxDepth) {
          const all_classes = (current.className && typeof current.className === 'string')
            ? current.className.trim().split(/\s+/)
            : [];
          const stable_classes = all_classes
            .filter(c => c && !/^ng[A-Z-]|_ng[a-z]|^cdk-|\d{4,}/.test(c))
            .slice(0, 3);
          ancestors.push({
            tag:          current.tagName.toLowerCase(),
            id:           current.id || null,
            role:         current.getAttribute('role')       || null,
            aria_label:   current.getAttribute('aria-label') || null,
            data_testid:  current.getAttribute('data-testid') || null,
            classes_stable: stable_classes,
          });
          // Salir si encontramos un landmark claro (no seguir subiendo)
          if (current.id || current.getAttribute('role') || current.getAttribute('data-testid')) {
            break;
          }
          current = current.parentElement;
          depth++;
        }
        return ancestors;
      }

      // ── Self-Healing: Detección de Shadow DOM (Angular ShadowDom mode) ────────
      function detectShadow(composedPath) {
        composedPath = composedPath || [];
        let shadowDepth = 0;
        let hostSelector = null;
        let hostXPath    = null;
        let innerSelector = null;
        for (let i = 0; i < composedPath.length; i++) {
          const node = composedPath[i];
          if (node && node.nodeType === 11) { // nodeType 11 = ShadowRoot
            shadowDepth++;
            if (!hostSelector) {
              const host = node.host;
              if (host) {
                if (host.id) {
                  hostSelector = '#' + CSS.escape(host.id);
                } else if (host.getAttribute('data-testid')) {
                  hostSelector = '[data-testid="' + host.getAttribute('data-testid') + '"]';
                } else if (host.getAttribute('aria-label')) {
                  hostSelector = host.tagName.toLowerCase() + '[aria-label="' + host.getAttribute('aria-label') + '"]';
                } else {
                  hostSelector = host.tagName.toLowerCase();
                }
                hostXPath = getXPathForElement(host);
              }
            }
          }
          // Capturar selector del elemento justo antes del primer ShadowRoot
          if (shadowDepth > 0 && node && node.nodeType === Node.ELEMENT_NODE && !innerSelector) {
            if (node.id) {
              innerSelector = '#' + CSS.escape(node.id);
            } else if (node.getAttribute('data-testid')) {
              innerSelector = '[data-testid="' + node.getAttribute('data-testid') + '"]';
            } else if (node.getAttribute('aria-label')) {
              innerSelector = node.tagName.toLowerCase() + '[aria-label="' + node.getAttribute('aria-label') + '"]';
            }
          }
        }
        return {
          is_shadow_child: shadowDepth > 0,
          host_selector:   hostSelector,
          host_xpath:      hostXPath,
          inner_selector:  innerSelector,
          depth:           shadowDepth,
        };
      }

      // ── Self-Healing: DOM podado alrededor del elemento interactuado ──────────
      function getPrunedDOM(el, maxAncestorDepth, maxBytes) {
        maxAncestorDepth = maxAncestorDepth || 2;
        maxBytes         = maxBytes         || 4096;
        try {
          // Subir N niveles para obtener el contenedor relevante
          let root = el;
          for (let i = 0; i < maxAncestorDepth; i++) {
            const p = root.parentElement;
            if (p && p !== document.body && p !== document.documentElement) {
              root = p;
            } else {
              break;
            }
          }
          const clone = root.cloneNode(true);
          // Eliminar nodos que no aportan contexto semántico
          ['script', 'style', 'svg', 'iframe', 'noscript', 'canvas', 'video', 'audio'].forEach(tag => {
            clone.querySelectorAll(tag).forEach(function(n) { n.remove(); });
          });
          // Podar atributos generados (Angular, frameworks)
          const PRUNE_ATTR_RE = /_ngcontent|_nghost|ng-version|__ngContext|ng-reflect|data-v-[0-9a-f]/;
          clone.querySelectorAll('*').forEach(function(node) {
            const toRemove = [];
            Array.from(node.attributes).forEach(function(attr) {
              if (PRUNE_ATTR_RE.test(attr.name)) {
                toRemove.push(attr.name);
              } else if (attr.name === 'class') {
                const pruned = attr.value.trim().split(/\s+/)
                  .filter(function(c) { return c && !/^ng[A-Z-]|_ng[a-z]|^cdk-/.test(c); })
                  .slice(0, 3);
                node.setAttribute('class', pruned.join(' '));
              }
            });
            toRemove.forEach(function(a) { node.removeAttribute(a); });
          });
          let html = clone.outerHTML || '';
          if (html.length > maxBytes) {
            html = html.slice(0, maxBytes) + '…[truncated]';
          }
          return html;
        } catch (_e) {
          return '';
        }
      }

      let highlightOverlay = null;
      function ensureHighlightOverlay() {
        if (!highlightOverlay) {
          highlightOverlay = document.createElement('div');
          highlightOverlay.style.position = 'fixed';
          highlightOverlay.style.border = '2px solid #00bcd4';
          highlightOverlay.style.background = 'rgba(0,188,212,0.15)';
          highlightOverlay.style.pointerEvents = 'none';
          highlightOverlay.style.zIndex = 2147483647;
          highlightOverlay.style.display = 'none';
          document.body.appendChild(highlightOverlay);
        }
      }

      function highlightElement(el) {
        if (!el || el === document.body || el === document.documentElement) {
          if (highlightOverlay) highlightOverlay.style.display = 'none';
          return;
        }
        ensureHighlightOverlay();
        const rect = el.getBoundingClientRect();
        highlightOverlay.style.display = 'block';
        highlightOverlay.style.left = `${rect.left}px`;
        highlightOverlay.style.top = `${rect.top}px`;
        highlightOverlay.style.width = `${rect.width}px`;
        highlightOverlay.style.height = `${rect.height}px`;
      }

      // Throttling ultra-agresivo para mousemove en sesiones largas
      let mouseMoveTimer = null;
      let mouseMoveSkipCounter = 0;
      document.addEventListener('mousemove', (e) => {
        // Saltar más frames en sesiones largas
        if (++mouseMoveSkipCounter % 4 !== 0) return;
        
        if (mouseMoveTimer) return;
        
        mouseMoveTimer = setTimeout(() => {
          highlightElement(e.target);
          mouseMoveTimer = null;
        }, 32); // 30fps máximo
      }, true);

      function getSelector(el) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';
        
        if (el.id) {
          const idSelector = '#' + CSS.escape(el.id);
          try {
            if (document.querySelectorAll(idSelector).length === 1) {
              return idSelector;
            }
          } catch (_) {}
        }

        const specialAttributes = ['data-testid', 'aria-label', 'data-qa', 'data-cy', 'data-test'];
        for (const attr of specialAttributes) {
          const value = el.getAttribute(attr);
          if (value) {
            const selector = `[${attr}="${CSS.escape(value)}"]`;
            try {
              if (document.querySelectorAll(selector).length === 1) {
                return selector;
              }
            } catch (_) {}
          }
        }

        const tag = el.tagName.toLowerCase();
        const standardAttributes = ['name', 'role', 'type', 'alt', 'title'];
        for (const attr of standardAttributes) {
          const value = el.getAttribute(attr);
          if (value) {
            const selector = `${tag}[${attr}="${CSS.escape(value)}"]`;
            try {
              if (document.querySelectorAll(selector).length === 1) {
                return selector;
              }
            } catch (_) {}
          }
        }

        if (el.className && typeof el.className === 'string') {
          const classes = el.className.trim().split(/\s+/).filter(c => c).slice(0, 2);
          if (classes.length > 0) {
            const classSelector = `${tag}.${classes.map(c => CSS.escape(c)).join('.')}`;
            try {
              if (document.querySelectorAll(classSelector).length === 1) {
                return classSelector;
              }
            } catch (_) {}
          }
        }

        function generateSimpleSelector(element) {
          const tag = element.tagName.toLowerCase();
          let selector = tag;
          
          const siblings = Array.from(element.parentElement?.children || [])
            .filter(el => el.tagName.toLowerCase() === tag);
          
          if (siblings.length > 1) {
            const index = siblings.indexOf(element) + 1;
            selector = `${tag}:nth-child(${index})`;
          }
          
          let current = element;
          let parts = [selector];
          let depth = 0;
          
          while (current.parentElement && depth < 3) {
            const parent = current.parentElement;
            const parentTag = parent.tagName.toLowerCase();
            
            if (parent.id) {
              parts.unshift(`#${CSS.escape(parent.id)}`);
              break;
            }
            
            const parentSiblings = Array.from(parent.parentElement?.children || [])
              .filter(el => el.tagName.toLowerCase() === parentTag);
            
            let parentSelector = parentTag;
            if (parentSiblings.length > 1) {
              const parentIndex = parentSiblings.indexOf(parent) + 1;
              parentSelector = `${parentTag}:nth-child(${parentIndex})`;
            }
            
            parts.unshift(parentSelector);
            current = parent;
            depth++;
          }
          
          return parts.join(' > ');
        }

        const simpleSelector = generateSimpleSelector(el);
        try {
          if (document.querySelectorAll(simpleSelector).length === 1) {
            return simpleSelector;
          }
        } catch (_) {}

        const fallbackSelector = `${tag}[data-recorded="${Date.now()}"]`;
        el.setAttribute('data-recorded', Date.now().toString());
        return fallbackSelector;
      }

      function metaForAction(el, selector, kind, composedPath) {
        const xp          = getXPathForElement(el);
        const tag         = el && el.tagName ? el.tagName.toLowerCase() : '';
        const id          = el && el.id ? el.id : '';
        const fingerprint = getElementFingerprint(el);
        const ancestors   = getAncestorChain(el, 4);
        const shadow      = detectShadow(composedPath || []);
        const pruned_dom  = getPrunedDOM(el, 2, 4096);
        return { kind, selector, xpath: xp, tag, id, fingerprint, ancestors, shadow, pruned_dom };
      }

      document.addEventListener('click', (e) => {
        const el = e.target;
        const selector = getSelector(el);
        if (selector) {
          // composedPath() debe capturarse sincrónicamente durante el evento
          const path = e.composedPath ? e.composedPath() : [];
          highlightElement(el);
          setTimeout(() => highlightOverlay && (highlightOverlay.style.display = 'none'), 300);
          const line = `await page.click('${selector}');`;
          window.logAction({ line, meta: metaForAction(el, selector, 'click', path) });
        }
      });

      // Optimización extrema para input events
      let inputTimer = null;
      let lastInputElement = null;
      let lastInputComposedPath = [];
      let inputActionCount = 0;
      
      document.addEventListener('input', (e) => {
        const el = e.target;
        // composedPath() capturado sincrónicamente en el evento
        const path = e.composedPath ? e.composedPath() : [];
        if (el.tagName === 'INPUT' && el.type === 'text') {
          lastInputElement = el;
          lastInputComposedPath = path;
          inputActionCount++;
          
          if (inputTimer) {
            clearTimeout(inputTimer);
          }
          
          // Delay adaptivo basado en cantidad de acciones
          const delay = inputActionCount > 100 ? 500 : 200;
          
          inputTimer = setTimeout(() => {
            const inputEl  = lastInputElement;
            const inputPath = lastInputComposedPath;
            const selector = getSelector(inputEl);
            const val = (inputEl.value || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            const line = `await page.type('${selector}', '${val}');`;
            window.logAction({ line, meta: metaForAction(inputEl, selector, 'type', inputPath) });
            inputTimer = null;
          }, delay);
        }
      });

      document.addEventListener('change', (e) => {
        const el = e.target;
        const path = e.composedPath ? e.composedPath() : [];
        const selector = getSelector(el);
        if (el.tagName === 'SELECT') {
          const line = `await page.select('${selector}', '${el.value}');`;
          window.logAction({ line, meta: metaForAction(el, selector, 'select', path) });
        } else if (el.type === 'checkbox') {
          const line = `await page.click('${selector}'); // checkbox ${el.checked ? 'checked' : 'unchecked'}`;
          window.logAction({ line, meta: metaForAction(el, selector, 'checkbox', path) });
        } else if (el.type === 'radio') {
          const line = `await page.click('${selector}'); // radio selected`;
          window.logAction({ line, meta: metaForAction(el, selector, 'radio', path) });
        }
      });
    });

    await page.goto(targetUrl);
    initialUrl = page.url();

    // Signal to Python that the browser is open and the URL is loaded.
    // Python uses this to start video recording only from this point.
    console.log('BROWSER_READY');

    console.log('\n[Recorder] Comienza a interactuar con la página.');
    console.log('[Recorder] Cierra el navegador para guardar las acciones.\n');

    const windowInfo = await page.evaluate(() => {
        return {
            x: window.screenX || 0,
            y: window.screenY || 0,
            width: window.outerWidth || window.innerWidth || 1280,
            height: window.outerHeight || window.innerHeight || 720
        };
    });
    console.log('WINDOW_INFO:' + JSON.stringify(windowInfo));

    browser.on('disconnected', () => {
        // Limpiar todos los timers
        if (logActionProcessor) {
          clearTimeout(logActionProcessor);
        }
        
        // Procesar acciones pendientes de manera síncrona y rápida
        if (logActionQueue.length > 0) {
          logActionQueue.forEach(action => {
            console.log('[Recorded]', action);
            actionRecorder.write(action);
          });
          logActionQueue = [];
        }
        
        actionRecorder.end();
    });

  } catch (error) {
    console.error('Error en Puppeteer:', error);
    if (actionRecorder) {
      actionRecorder.destroy();
    }
    process.exit(1);
  }
})();