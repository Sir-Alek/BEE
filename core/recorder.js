// recorder.js
const fs = require('fs');
const path = require('path');
const puppeteer = require(path.join(__dirname, 'node', 'node_modules', 'puppeteer'));

const actions = [];
let initialUrl = '';
let lastInputAction = null;
let inputTimeout = null;

(async () => {
  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    args: ['--start-maximized']
  });

  const page = await browser.newPage();

  // Exponer función para registrar acciones desde el navegador
  await page.exposeFunction('logAction', (action) => {
    console.log('[Recorded]', action);
    
    // Manejar acciones de tipo input (sin cambios)
    if (action.startsWith('await page.type(')) {
      if (lastInputAction && action.split("'")[1] === lastInputAction.selector) {
        lastInputAction.action = action;
        clearTimeout(inputTimeout);
      } else {
        if (lastInputAction) {
          actions.push(lastInputAction.action);
        }
        lastInputAction = { selector: action.split("'")[1], action };
      }
      
      inputTimeout = setTimeout(() => {
        if (lastInputAction) {
          actions.push(lastInputAction.action);
          lastInputAction = null;
        }
      }, 500);
    } else {
      if (lastInputAction) {
        actions.push(lastInputAction.action);
        lastInputAction = null;
      }
      actions.push(action);
    }
  });

  // Inyectar script antes de cada documento 
  await page.evaluateOnNewDocument(() => {
    function getSelector(el) {
      // 1. Priorizar ID si existe
      if (el.id) {
        return '#' + el.id;
      }

      // 2. Buscar atributos únicos (data-testid, aria-label, etc.)
      const uniqueAttributes = ['data-testid', 'aria-label', 'name', 'role', 'type', 'alt', 'title'];
      for (const attr of uniqueAttributes) {
        const value = el.getAttribute(attr);
        if (value) {
          return `[${attr}="${value}"]`;
        }
      }

      // 3. Combinar etiqueta + clases si existen
      if (el.className && typeof el.className === 'string') {
        const classes = el.className.trim().split(/\s+/).filter(c => c).join('.');
        if (classes) {
          // Verificar si el selector es único
          if (document.querySelectorAll(`${el.tagName.toLowerCase()}.${classes}`).length === 1) {
            return `${el.tagName.toLowerCase()}.${classes}`;
          }
        }
      }

      // 4. Usar selector de ruta si hay elementos padre con ID
      const pathSegments = [];
      let currentElement = el;
      
      while (currentElement && currentElement !== document.body) {
        let segment = '';
        
        // Priorizar ID en elementos padre
        if (currentElement.id) {
          pathSegments.unshift('#' + currentElement.id);
          break;
        }
        
        // Usar etiqueta + índice entre hermanos
        if (currentElement.parentElement) {
          const siblings = Array.from(currentElement.parentElement.children);
          const sameTagSiblings = siblings.filter(s => s.tagName === currentElement.tagName);
          const index = sameTagSiblings.indexOf(currentElement) + 1;
          
          segment = sameTagSiblings.length > 1 
            ? `${currentElement.tagName.toLowerCase()}:nth-of-type(${index})`
            : currentElement.tagName.toLowerCase();
        } else {
          segment = currentElement.tagName.toLowerCase();
        }
        
        pathSegments.unshift(segment);
        currentElement = currentElement.parentElement;
      }
      
      return pathSegments.join(' > ');
    }

    document.addEventListener('click', (e) => {
      const el = e.target;
      const selector = getSelector(el);
      if (selector) {
        window.logAction(`await page.click('${selector}');`);
      }
    });

    document.addEventListener('input', (e) => {
      const el = e.target;
      if (el.tagName === 'INPUT' && el.type === 'text') {
        const selector = getSelector(el);
        window.logAction(`await page.type('${selector}', '${el.value}');`);
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

  await page.goto('https://www.google.com');
  initialUrl = page.url();

  console.log('\n[Recorder] Comienza a interactuar con la página.');
  console.log('[Recorder] Cierra el navegador para guardar las acciones.\n');

  // Aceptar el nombre de archivo como argumento
  const outputFile = process.argv[2] || path.join(__dirname, 'grabaciones', 'recorded_actions.js');

  // Modificar el evento disconnected
  browser.on('disconnected', () => {
      if (lastInputAction) {
        actions.push(lastInputAction.action);
      }
      
      const scriptContent = `/* URL: ${initialUrl} */\n` + 
          `const puppeteer = require('puppeteer');\n\n` +
          `(async () => {\n` +
          `  const browser = await puppeteer.launch({ headless: false });\n` +
          `  const page = await browser.newPage();\n` +
          `  await page.goto('${initialUrl}');\n\n` +
          `${actions.join('\n')}\n\n` +
          `  await browser.close();\n` +
          `})();`;
      
      fs.writeFileSync(outputFile, scriptContent, 'utf-8');
      console.log(`FILE_SAVED:${outputFile}`);
  });
})();