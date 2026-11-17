const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const base = path.resolve(__dirname, '../urano');
const strings = JSON.parse(fs.readFileSync(path.join(base, 'work_strings.json')));
const staticLabel = {textContent:' Footage ', parentElement:{closest:() => null}};
const projectTitle = {textContent:'Footage'};
const progress = {set textContent(text) { this.firstChild = {textContent:text, isConnected:true}; }};
const document = {
  createTreeWalker() {
    const nodes = [staticLabel][Symbol.iterator]();
    return {nextNode:() => nodes.next().value};
  },
  documentElement:{}
};
const window = {MontaraWorkStrings:strings};
vm.runInNewContext(fs.readFileSync(path.join(base, 'work_i18n.js'), 'utf8'),
  {window, document, NodeFilter:{SHOW_TEXT:4}});
const i18n = window.MontaraWorkI18n;
i18n.captureStatic({querySelectorAll:() => []});
i18n.setText(progress, 'Saving…');
for (const [index, locale] of ['es', 'de', 'fr', 'en'].entries()) {
  i18n.setLocale(locale);
  assert.equal(document.documentElement.lang, locale);
  assert.equal(staticLabel.textContent, ' ' + (strings.Footage[index] || 'Footage') + ' ');
  assert.equal(progress.firstChild.textContent, strings['Saving…'][index] || 'Saving…');
  assert.equal(projectTitle.textContent, 'Footage');
  assert.equal(i18n.translate('Unmapped string'), 'Unmapped string');
}
