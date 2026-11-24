const fs=require('node:fs'),assert=require('node:assert/strict');const path=require('node:path');
const dir=path.join(__dirname,'../ops/main/jm-approved-promotion');
const builder=fs.readFileSync(path.join(dir,'build_overlay.py'),'utf8');
const buttons=fs.readFileSync(path.join(dir,'owner_buttons.fragment'),'utf8');
for(const item of ['main-project-name-overlay-20261121','EXPECTED','PRESERVED_MAIN_FULL_SESSION','PRESERVED_MAIN_GATEWAY','PRESERVED_MAIN_COMPANION','co_lead_vocal','choir']) assert.ok(builder.includes(item));
for(const item of ['/api/v1/wizard/projects/open','/api/v1/wizard/projects/delete','keep_exports:true','montara-open-edit','confirm(']) assert.ok(buttons.includes(item));
console.log('MAIN_JM_PROMOTION_PLAN_STATIC_PASS');
