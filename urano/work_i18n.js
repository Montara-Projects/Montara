/* Work UI strings only. User content never passes through this registry. */
(() => {
  'use strict';
  const strings = window.MontaraWorkStrings;
  const textNodes = new Map();
  const attributes = [];
  const dynamic = new Map();
  let language = 'en';
  const translate = text => Object.hasOwn(strings, text)
    ? strings[text][['es', 'de', 'fr'].indexOf(language)] || text : text;
  window.MontaraWorkI18n = {
    translate,
    captureStatic(root) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!node.parentElement.closest('script, style, textarea') &&
            Object.hasOwn(strings, node.textContent.trim())) textNodes.set(node, node.textContent);
      }
      for (const element of root.querySelectorAll('[aria-label], [placeholder], [title]')) {
        for (const name of ['aria-label', 'placeholder', 'title']) {
          const label = element.getAttribute(name);
          if (Object.hasOwn(strings, label)) attributes.push([element, name, label]);
        }
      }
    },
    setText(element, key) {
      element.textContent = translate(key);
      if (element.firstChild) dynamic.set(element.firstChild, key);
    },
    setLocale(locale) {
      language = ['en', 'es', 'de', 'fr'].includes(locale) ? locale : 'en';
      document.documentElement.lang = language;
      for (const [node, original] of textNodes) {
        node.textContent = original.replace(original.trim(), translate(original.trim()));
      }
      for (const [element, name, original] of attributes) {
        element.setAttribute(name, translate(original));
      }
      for (const [node, key] of dynamic) {
        if (node.isConnected) node.textContent = translate(key);
        else dynamic.delete(node);
      }
    }
  };
})();
