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
        const webdriverPath = path.join(__dirname, 'node', 'node_modules', 'webdriver-manager');
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
const puppeteer = require(path.join(__dirname, 'node', 'node_modules', 'puppeteer'));
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

        this._processAction(action, callback);
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
        '--disable-features=IsolateOrigins,site-per-process'
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

      document.addEventListener('click', (e) => {
        const el = e.target;
        const selector = getSelector(el);
        if (selector) {
          highlightElement(el);
          setTimeout(() => highlightOverlay && (highlightOverlay.style.display = 'none'), 300);
          
          window.logAction(`await page.click('${selector}');`);
        }
      });

      // Optimización extrema para input events
      let inputTimer = null;
      let lastInputElement = null;
      let inputActionCount = 0;
      
      document.addEventListener('input', (e) => {
        const el = e.target;
        if (el.tagName === 'INPUT' && el.type === 'text') {
          lastInputElement = el;
          inputActionCount++;
          
          if (inputTimer) {
            clearTimeout(inputTimer);
          }
          
          // Delay adaptivo basado en cantidad de acciones
          const delay = inputActionCount > 100 ? 500 : 200;
          
          inputTimer = setTimeout(() => {
            const selector = getSelector(lastInputElement);
            window.logAction(`await page.type('${selector}', '${lastInputElement.value}');`);
            inputTimer = null;
          }, delay);
        }
      });

      document.addEventListener('change', (e) => {
        const el = e.target;
        const selector = getSelector(el);
        if (el.tagName === 'SELECT') {
          window.logAction(`await page.select('${selector}', '${el.value}');`);
        } else if (el.type === 'checkbox') {
          window.logAction(`await page.click('${selector}'); // checkbox ${el.checked ? 'checked' : 'unchecked'}`);
        } else if (el.type === 'radio') {
          window.logAction(`await page.click('${selector}'); // radio selected`);
        }
      });
    });

    await page.goto(targetUrl);
    initialUrl = page.url();

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