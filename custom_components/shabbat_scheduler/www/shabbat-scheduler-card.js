/******************************************************************************
Copyright (c) Microsoft Corporation.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
***************************************************************************** */
/* global Reflect, Promise, SuppressedError, Symbol, Iterator */


function __decorate(decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
}

typeof SuppressedError === "function" ? SuppressedError : function (error, suppressed, message) {
    var e = new Error(message);
    return e.name = "SuppressedError", e.error = error, e.suppressed = suppressed, e;
};

/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t$3=globalThis,e$2=t$3.ShadowRoot&&(void 0===t$3.ShadyCSS||t$3.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s$2=Symbol(),o$4=new WeakMap;let n$3 = class n{constructor(t,e,o){if(this._$cssResult$=true,o!==s$2)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e;}get styleSheet(){let t=this.o;const s=this.t;if(e$2&&void 0===t){const e=void 0!==s&&1===s.length;e&&(t=o$4.get(s)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),e&&o$4.set(s,t));}return t}toString(){return this.cssText}};const r$4=t=>new n$3("string"==typeof t?t:t+"",void 0,s$2),i$3=(t,...e)=>{const o=1===t.length?t[0]:e.reduce((e,s,o)=>e+(t=>{if(true===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[o+1],t[0]);return new n$3(o,t,s$2)},S$1=(s,o)=>{if(e$2)s.adoptedStyleSheets=o.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const e of o){const o=document.createElement("style"),n=t$3.litNonce;void 0!==n&&o.setAttribute("nonce",n),o.textContent=e.cssText,s.appendChild(o);}},c$2=e$2?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return r$4(e)})(t):t;

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:i$2,defineProperty:e$1,getOwnPropertyDescriptor:h$1,getOwnPropertyNames:r$3,getOwnPropertySymbols:o$3,getPrototypeOf:n$2}=Object,a$1=globalThis,c$1=a$1.trustedTypes,l$1=c$1?c$1.emptyScript:"",p$1=a$1.reactiveElementPolyfillSupport,d$1=(t,s)=>t,u$1={toAttribute(t,s){switch(s){case Boolean:t=t?l$1:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t);}return t},fromAttribute(t,s){let i=t;switch(s){case Boolean:i=null!==t;break;case Number:i=null===t?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t);}catch(t){i=null;}}return i}},f$1=(t,s)=>!i$2(t,s),b$1={attribute:true,type:String,converter:u$1,reflect:false,useDefault:false,hasChanged:f$1};Symbol.metadata??=Symbol("metadata"),a$1.litPropertyMetadata??=new WeakMap;let y$1 = class y extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t);}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,s=b$1){if(s.state&&(s.attribute=false),this._$Ei(),this.prototype.hasOwnProperty(t)&&((s=Object.create(s)).wrapped=true),this.elementProperties.set(t,s),!s.noAccessor){const i=Symbol(),h=this.getPropertyDescriptor(t,i,s);void 0!==h&&e$1(this.prototype,t,h);}}static getPropertyDescriptor(t,s,i){const{get:e,set:r}=h$1(this.prototype,t)??{get(){return this[s]},set(t){this[s]=t;}};return {get:e,set(s){const h=e?.call(this);r?.call(this,s),this.requestUpdate(t,h,i);},configurable:true,enumerable:true}}static getPropertyOptions(t){return this.elementProperties.get(t)??b$1}static _$Ei(){if(this.hasOwnProperty(d$1("elementProperties")))return;const t=n$2(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties);}static finalize(){if(this.hasOwnProperty(d$1("finalized")))return;if(this.finalized=true,this._$Ei(),this.hasOwnProperty(d$1("properties"))){const t=this.properties,s=[...r$3(t),...o$3(t)];for(const i of s)this.createProperty(i,t[i]);}const t=this[Symbol.metadata];if(null!==t){const s=litPropertyMetadata.get(t);if(void 0!==s)for(const[t,i]of s)this.elementProperties.set(t,i);}this._$Eh=new Map;for(const[t,s]of this.elementProperties){const i=this._$Eu(t,s);void 0!==i&&this._$Eh.set(i,t);}this.elementStyles=this.finalizeStyles(this.styles);}static finalizeStyles(s){const i=[];if(Array.isArray(s)){const e=new Set(s.flat(1/0).reverse());for(const s of e)i.unshift(c$2(s));}else void 0!==s&&i.push(c$2(s));return i}static _$Eu(t,s){const i=s.attribute;return  false===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=false,this.hasUpdated=false,this._$Em=null,this._$Ev();}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this));}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.();}removeController(t){this._$EO?.delete(t);}_$E_(){const t=new Map,s=this.constructor.elementProperties;for(const i of s.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t);}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return S$1(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(true),this._$EO?.forEach(t=>t.hostConnected?.());}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.());}attributeChangedCallback(t,s,i){this._$AK(t,i);}_$ET(t,s){const i=this.constructor.elementProperties.get(t),e=this.constructor._$Eu(t,i);if(void 0!==e&&true===i.reflect){const h=(void 0!==i.converter?.toAttribute?i.converter:u$1).toAttribute(s,i.type);this._$Em=t,null==h?this.removeAttribute(e):this.setAttribute(e,h),this._$Em=null;}}_$AK(t,s){const i=this.constructor,e=i._$Eh.get(t);if(void 0!==e&&this._$Em!==e){const t=i.getPropertyOptions(e),h="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:u$1;this._$Em=e;const r=h.fromAttribute(s,t.type);this[e]=r??this._$Ej?.get(e)??r,this._$Em=null;}}requestUpdate(t,s,i,e=false,h){if(void 0!==t){const r=this.constructor;if(false===e&&(h=this[t]),i??=r.getPropertyOptions(t),!((i.hasChanged??f$1)(h,s)||i.useDefault&&i.reflect&&h===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,i))))return;this.C(t,s,i);} false===this.isUpdatePending&&(this._$ES=this._$EP());}C(t,s,{useDefault:i,reflect:e,wrapped:h},r){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??s??this[t]),true!==h||void 0!==r)||(this._$AL.has(t)||(this.hasUpdated||i||(s=void 0),this._$AL.set(t,s)),true===e&&this._$Em!==t&&(this._$Eq??=new Set).add(t));}async _$EP(){this.isUpdatePending=true;try{await this._$ES;}catch(t){Promise.reject(t);}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,s]of this._$Ep)this[t]=s;this._$Ep=void 0;}const t=this.constructor.elementProperties;if(t.size>0)for(const[s,i]of t){const{wrapped:t}=i,e=this[s];true!==t||this._$AL.has(s)||void 0===e||this.C(s,void 0,i,e);}}let t=false;const s=this._$AL;try{t=this.shouldUpdate(s),t?(this.willUpdate(s),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(s)):this._$EM();}catch(s){throw t=false,this._$EM(),s}t&&this._$AE(s);}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=true,this.firstUpdated(t)),this.updated(t);}_$EM(){this._$AL=new Map,this.isUpdatePending=false;}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return  true}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM();}updated(t){}firstUpdated(t){}};y$1.elementStyles=[],y$1.shadowRootOptions={mode:"open"},y$1[d$1("elementProperties")]=new Map,y$1[d$1("finalized")]=new Map,p$1?.({ReactiveElement:y$1}),(a$1.reactiveElementVersions??=[]).push("2.1.2");

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t$2=globalThis,i$1=t=>t,s$1=t$2.trustedTypes,e=s$1?s$1.createPolicy("lit-html",{createHTML:t=>t}):void 0,h="$lit$",o$2=`lit$${Math.random().toFixed(9).slice(2)}$`,n$1="?"+o$2,r$2=`<${n$1}>`,l=document,c=()=>l.createComment(""),a=t=>null===t||"object"!=typeof t&&"function"!=typeof t,u=Array.isArray,d=t=>u(t)||"function"==typeof t?.[Symbol.iterator],f="[ \t\n\f\r]",v=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,_=/-->/g,m=/>/g,p=RegExp(`>|${f}(?:([^\\s"'>=/]+)(${f}*=${f}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),g=/'/g,$=/"/g,y=/^(?:script|style|textarea|title)$/i,x=t=>(i,...s)=>({_$litType$:t,strings:i,values:s}),b=x(1),E=Symbol.for("lit-noChange"),A=Symbol.for("lit-nothing"),C=new WeakMap,P=l.createTreeWalker(l,129);function V(t,i){if(!u(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==e?e.createHTML(i):i}const N=(t,i)=>{const s=t.length-1,e=[];let n,l=2===i?"<svg>":3===i?"<math>":"",c=v;for(let i=0;i<s;i++){const s=t[i];let a,u,d=-1,f=0;for(;f<s.length&&(c.lastIndex=f,u=c.exec(s),null!==u);)f=c.lastIndex,c===v?"!--"===u[1]?c=_:void 0!==u[1]?c=m:void 0!==u[2]?(y.test(u[2])&&(n=RegExp("</"+u[2],"g")),c=p):void 0!==u[3]&&(c=p):c===p?">"===u[0]?(c=n??v,d=-1):void 0===u[1]?d=-2:(d=c.lastIndex-u[2].length,a=u[1],c=void 0===u[3]?p:'"'===u[3]?$:g):c===$||c===g?c=p:c===_||c===m?c=v:(c=p,n=void 0);const x=c===p&&t[i+1].startsWith("/>")?" ":"";l+=c===v?s+r$2:d>=0?(e.push(a),s.slice(0,d)+h+s.slice(d)+o$2+x):s+o$2+(-2===d?i:x);}return [V(t,l+(t[s]||"<?>")+(2===i?"</svg>":3===i?"</math>":"")),e]};class S{constructor({strings:t,_$litType$:i},e){let r;this.parts=[];let l=0,a=0;const u=t.length-1,d=this.parts,[f,v]=N(t,i);if(this.el=S.createElement(f,e),P.currentNode=this.el.content,2===i||3===i){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes);}for(;null!==(r=P.nextNode())&&d.length<u;){if(1===r.nodeType){if(r.hasAttributes())for(const t of r.getAttributeNames())if(t.endsWith(h)){const i=v[a++],s=r.getAttribute(t).split(o$2),e=/([.?@])?(.*)/.exec(i);d.push({type:1,index:l,name:e[2],strings:s,ctor:"."===e[1]?I:"?"===e[1]?L:"@"===e[1]?z:H}),r.removeAttribute(t);}else t.startsWith(o$2)&&(d.push({type:6,index:l}),r.removeAttribute(t));if(y.test(r.tagName)){const t=r.textContent.split(o$2),i=t.length-1;if(i>0){r.textContent=s$1?s$1.emptyScript:"";for(let s=0;s<i;s++)r.append(t[s],c()),P.nextNode(),d.push({type:2,index:++l});r.append(t[i],c());}}}else if(8===r.nodeType)if(r.data===n$1)d.push({type:2,index:l});else {let t=-1;for(;-1!==(t=r.data.indexOf(o$2,t+1));)d.push({type:7,index:l}),t+=o$2.length-1;}l++;}}static createElement(t,i){const s=l.createElement("template");return s.innerHTML=t,s}}function M(t,i,s=t,e){if(i===E)return i;let h=void 0!==e?s._$Co?.[e]:s._$Cl;const o=a(i)?void 0:i._$litDirective$;return h?.constructor!==o&&(h?._$AO?.(false),void 0===o?h=void 0:(h=new o(t),h._$AT(t,s,e)),void 0!==e?(s._$Co??=[])[e]=h:s._$Cl=h),void 0!==h&&(i=M(t,h._$AS(t,i.values),h,e)),i}class R{constructor(t,i){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=i;}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:i},parts:s}=this._$AD,e=(t?.creationScope??l).importNode(i,true);P.currentNode=e;let h=P.nextNode(),o=0,n=0,r=s[0];for(;void 0!==r;){if(o===r.index){let i;2===r.type?i=new k(h,h.nextSibling,this,t):1===r.type?i=new r.ctor(h,r.name,r.strings,this,t):6===r.type&&(i=new Z(h,this,t)),this._$AV.push(i),r=s[++n];}o!==r?.index&&(h=P.nextNode(),o++);}return P.currentNode=l,e}p(t){let i=0;for(const s of this._$AV) void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,i),i+=s.strings.length-2):s._$AI(t[i])),i++;}}class k{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,i,s,e){this.type=2,this._$AH=A,this._$AN=void 0,this._$AA=t,this._$AB=i,this._$AM=s,this.options=e,this._$Cv=e?.isConnected??true;}get parentNode(){let t=this._$AA.parentNode;const i=this._$AM;return void 0!==i&&11===t?.nodeType&&(t=i.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,i=this){t=M(this,t,i),a(t)?t===A||null==t||""===t?(this._$AH!==A&&this._$AR(),this._$AH=A):t!==this._$AH&&t!==E&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):d(t)?this.k(t):this._(t);}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t));}_(t){this._$AH!==A&&a(this._$AH)?this._$AA.nextSibling.data=t:this.T(l.createTextNode(t)),this._$AH=t;}$(t){const{values:i,_$litType$:s}=t,e="number"==typeof s?this._$AC(t):(void 0===s.el&&(s.el=S.createElement(V(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===e)this._$AH.p(i);else {const t=new R(e,this),s=t.u(this.options);t.p(i),this.T(s),this._$AH=t;}}_$AC(t){let i=C.get(t.strings);return void 0===i&&C.set(t.strings,i=new S(t)),i}k(t){u(this._$AH)||(this._$AH=[],this._$AR());const i=this._$AH;let s,e=0;for(const h of t)e===i.length?i.push(s=new k(this.O(c()),this.O(c()),this,this.options)):s=i[e],s._$AI(h),e++;e<i.length&&(this._$AR(s&&s._$AB.nextSibling,e),i.length=e);}_$AR(t=this._$AA.nextSibling,s){for(this._$AP?.(false,true,s);t!==this._$AB;){const s=i$1(t).nextSibling;i$1(t).remove(),t=s;}}setConnected(t){ void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t));}}class H{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,i,s,e,h){this.type=1,this._$AH=A,this._$AN=void 0,this.element=t,this.name=i,this._$AM=e,this.options=h,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=A;}_$AI(t,i=this,s,e){const h=this.strings;let o=false;if(void 0===h)t=M(this,t,i,0),o=!a(t)||t!==this._$AH&&t!==E,o&&(this._$AH=t);else {const e=t;let n,r;for(t=h[0],n=0;n<h.length-1;n++)r=M(this,e[s+n],i,n),r===E&&(r=this._$AH[n]),o||=!a(r)||r!==this._$AH[n],r===A?t=A:t!==A&&(t+=(r??"")+h[n+1]),this._$AH[n]=r;}o&&!e&&this.j(t);}j(t){t===A?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"");}}class I extends H{constructor(){super(...arguments),this.type=3;}j(t){this.element[this.name]=t===A?void 0:t;}}class L extends H{constructor(){super(...arguments),this.type=4;}j(t){this.element.toggleAttribute(this.name,!!t&&t!==A);}}class z extends H{constructor(t,i,s,e,h){super(t,i,s,e,h),this.type=5;}_$AI(t,i=this){if((t=M(this,t,i,0)??A)===E)return;const s=this._$AH,e=t===A&&s!==A||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,h=t!==A&&(s===A||e);e&&this.element.removeEventListener(this.name,this,s),h&&this.element.addEventListener(this.name,this,t),this._$AH=t;}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t);}}class Z{constructor(t,i,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=i,this.options=s;}get _$AU(){return this._$AM._$AU}_$AI(t){M(this,t);}}const B=t$2.litHtmlPolyfillSupport;B?.(S,k),(t$2.litHtmlVersions??=[]).push("3.3.3");const D=(t,i,s)=>{const e=s?.renderBefore??i;let h=e._$litPart$;if(void 0===h){const t=s?.renderBefore??null;e._$litPart$=h=new k(i.insertBefore(c(),t),t,void 0,s??{});}return h._$AI(t),h};

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const s=globalThis;class i extends y$1{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0;}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const r=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=D(r,this.renderRoot,this.renderOptions);}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(true);}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(false);}render(){return E}}i._$litElement$=true,i["finalized"]=true,s.litElementHydrateSupport?.({LitElement:i});const o$1=s.litElementPolyfillSupport;o$1?.({LitElement:i});(s.litElementVersions??=[]).push("4.2.2");

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t$1=t=>(e,o)=>{ void 0!==o?o.addInitializer(()=>{customElements.define(t,e);}):customElements.define(t,e);};

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const o={attribute:true,type:String,converter:u$1,reflect:false,hasChanged:f$1},r$1=(t=o,e,r)=>{const{kind:n,metadata:i}=r;let s=globalThis.litPropertyMetadata.get(i);if(void 0===s&&globalThis.litPropertyMetadata.set(i,s=new Map),"setter"===n&&((t=Object.create(t)).wrapped=true),s.set(r.name,t),"accessor"===n){const{name:o}=r;return {set(r){const n=e.get.call(this);e.set.call(this,r),this.requestUpdate(o,n,t,true,r);},init(e){return void 0!==e&&this.C(o,void 0,t,e),e}}}if("setter"===n){const{name:o}=r;return function(r){const n=this[o];e.call(this,r),this.requestUpdate(o,n,t,true,r);}}throw Error("Unsupported decorator location: "+n)};function n(t){return (e,o)=>"object"==typeof o?r$1(t,e,o):((t,e,o)=>{const r=e.hasOwnProperty(o);return e.constructor.createProperty(o,t),r?Object.getOwnPropertyDescriptor(e,o):void 0})(t,e,o)}

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function r(r){return n({...r,state:true,attribute:false})}

/** Mirrors the integration's own en/he translations. */
const STRINGS = {
    en: {
        erev: 'Erev',
        day: 'Day',
        candle_lighting: 'Candle lighting',
        havdalah: 'Havdalah',
        master: 'Shabbat Scheduler',
        dry_run: 'Dry run',
        no_block: 'No upcoming Shabbat could be derived from the Jewish Calendar sensors.',
        not_set_up: 'Shabbat Scheduler is not configured.',
        stale: 'Connection lost — showing the last known state.',
        // Deliberately distinct from `stale`. The server was reachable and
        // refused the call - saying "connection lost" there is a wrong
        // diagnosis that sends someone to check the network.
        command_failed: 'That did not go through. Nothing was changed.',
        no_rules: 'No rules for this block.',
        disabled_rule: 'disabled',
        conflict_prefix: 'Conflict',
    },
    he: {
        erev: 'ערב',
        day: 'יום',
        candle_lighting: 'הדלקת נרות',
        havdalah: 'הבדלה',
        master: 'שעון שבת',
        dry_run: 'הרצה יבשה',
        no_block: 'לא ניתן לגזור שבת קרובה מחיישני לוח השנה העברי.',
        not_set_up: 'שעון שבת אינו מוגדר.',
        stale: 'החיבור אבד — מוצג המצב האחרון הידוע.',
        command_failed: 'הפעולה לא בוצעה. שום דבר לא השתנה.',
        no_rules: 'אין כללים לבלוק הזה.',
        disabled_rule: 'מושבת',
        conflict_prefix: 'התנגשות',
    },
};
function t(language, key) {
    const table = language === 'he' ? STRINGS.he : STRINGS.en;
    return table[key];
}

/** Erev sorts before day 1, then days ascend numerically. */
function dayRank(day) {
    return day === 'erev' ? -1 : Number(day);
}
function dayKeys(block) {
    const days = ['erev'];
    for (let i = 1; i <= block.length; i += 1)
        days.push(String(i));
    return days;
}
/**
 * The block's dates in calendar order: erev, then day 1, day 2, ….
 *
 * `block.dates` is a plain object keyed 'erev' | '1' | '2' ..., and
 * JavaScript enumerates integer-index-like keys in ascending numeric
 * order *before* string keys - so 'erev' comes last no matter how the
 * object was built. Relying on Object.values/Object.keys order here
 * renders the block's dates backwards. Missing days are skipped rather
 * than surfaced as empty strings.
 */
function orderedDates(block) {
    return dayKeys(block)
        .map((day) => block.dates[day])
        .filter((date) => date !== undefined);
}
/**
 * The timeline: one group per day of the block, in order, each carrying
 * its date, its rules ordered by time, and its zmanim marker if one
 * falls at its end.
 *
 * Only rules matching the block's length are shown - rules are authored
 * per profile, and a 3-day chag's rules must not appear on a plain
 * Shabbat.
 */
function buildGroups(state) {
    const { block } = state;
    if (block === null)
        return [];
    const lastDay = String(block.length);
    return dayKeys(block).map((day) => {
        const rules = state.rules
            .filter((rule) => rule.profile === block.length && rule.day === day)
            .sort((a, b) => a.time.localeCompare(b.time));
        let marker = null;
        if (day === 'erev') {
            marker = { kind: 'candle_lighting', at: block.candle_lighting };
        }
        else if (day === lastDay) {
            marker = { kind: 'havdalah', at: block.havdalah };
        }
        return { day, date: block.dates[day] ?? null, rules, marker };
    }).sort((a, b) => dayRank(a.day) - dayRank(b.day));
}
/**
 * One line describing what a rule does, resolved exactly the way the
 * engine resolves it: the rule's own devices and settings win, and
 * anything it omits falls back to the defaults.
 */
function ruleBrief(rule, defaults) {
    if (rule.action === 'custom') {
        return rule.script ?? '';
    }
    const devices = rule.devices.length ? rule.devices : (defaults.devices ?? []);
    const settings = { ...(defaults.settings ?? {}), ...rule.settings };
    const parts = [devices.join(', ')];
    if (rule.action === 'on') {
        for (const value of Object.values(settings)) {
            if (value !== undefined && value !== null)
                parts.push(String(value));
        }
    }
    return parts.filter((part) => part !== '').join(' · ');
}
const COLOURS = {
    on: 'var(--success-color, #2e9e5b)',
    off: 'var(--error-color, #d64545)',
    custom: 'var(--info-color, #3b7ddd)',
};
function actionColour(action) {
    return COLOURS[action] ?? 'var(--secondary-text-color, #888)';
}
/** Warnings naming this rule, so a conflict shows where it happens. */
function warningsForRule(ruleId, warnings) {
    return warnings.filter((warning) => warning.rule_ids?.includes(ruleId));
}
/**
 * Warnings that have nowhere else to go, for the banner.
 *
 * `buildGroups` only shows rules whose profile matches the current
 * block length, but warnings are never filtered by profile. A warning
 * naming no rule, or naming only rules that are not among the ones
 * currently displayed, would otherwise be shown on no row and dropped
 * here too - rendered nowhere. Conflicts are never auto-resolved, so a
 * conflict nobody can see is exactly the failure this card exists to
 * prevent; it must surface in the banner instead.
 */
function unattachedWarnings(warnings, displayedRuleIds) {
    const displayed = new Set(displayedRuleIds);
    return warnings.filter((warning) => !warning.rule_ids?.some((id) => displayed.has(id)));
}
/** 'erev' -> 'Erev' / 'ערב'; '1' -> 'Day 1' / 'יום 1'. */
function dayLabel(day, language) {
    return day === 'erev' ? t(language, 'erev') : `${t(language, 'day')} ${day}`;
}
/**
 * A warning as prose a person can act on. The only warning this card's
 * `_state_payload` ever sends is a conflict - see the comment on
 * `WarningData` - which carries no `message`, so this is the sole place
 * a conflict becomes human-readable text, naming the device and the
 * time so the person who must resolve it (nothing here auto-resolves)
 * knows exactly what to look at.
 *
 * Falls back to `message` for the `preview_payload` shape this card
 * does not currently receive, so a stray warning still renders as
 * something rather than nothing.
 */
function formatWarning(warning, language) {
    if (warning.kind === 'conflict' && warning.device !== undefined && warning.time !== undefined) {
        const parts = [t(language, 'conflict_prefix'), warning.device];
        if (warning.day !== undefined)
            parts.push(dayLabel(warning.day, language));
        parts.push(warning.time);
        return parts.join(' · ');
    }
    return warning.message ?? '';
}

let ShabbatBlockHeader = class ShabbatBlockHeader extends i {
    constructor() {
        super(...arguments);
        this.block = null;
        this.enabled = false;
        this.dryRun = false;
        this.canWrite = false;
        this.masterEntityId = null;
        this.language = 'en';
    }
    _dates() {
        if (this.block === null)
            return '';
        return orderedDates(this.block).join(' → ');
    }
    // No optimistic update anywhere here: the control reports intent and
    // keeps rendering the pushed state until the server confirms.
    _toggleMaster() {
        this.dispatchEvent(new CustomEvent('shabbat-master-toggle', {
            detail: { enabled: !this.enabled },
        }));
    }
    _toggleDryRun() {
        this.dispatchEvent(new CustomEvent('shabbat-dry-run-toggle', {
            detail: { dryRun: !this.dryRun },
        }));
    }
    render() {
        return b `
      <div class="header">
        <div class="label">
          ${this.block === null
            ? b `<span class="none">${t(this.language, 'no_block')}</span>`
            : b `
                <span>${t(this.language, 'day')} ×${this.block.length}</span>
                <span class="dates">${this._dates()}</span>
              `}
        </div>
        <button
          class="master ${this.enabled ? 'active' : ''}"
          ?disabled=${!this.canWrite || this.masterEntityId === null}
          @click=${this._toggleMaster}
        >
          ${t(this.language, 'master')}
        </button>
        <button
          class="dry-run ${this.dryRun ? 'active' : ''}"
          ?disabled=${!this.canWrite}
          @click=${this._toggleDryRun}
        >
          ${t(this.language, 'dry_run')}
        </button>
      </div>
    `;
    }
};
ShabbatBlockHeader.styles = i$3 `
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      padding-block-end: 8px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .label { flex: 1; min-inline-size: 0; font-weight: 600; }
    .dates { color: var(--secondary-text-color, #666); font-weight: 400; }
    button {
      font: inherit;
      padding-block: 4px;
      padding-inline: 10px;
      border-radius: 14px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    button.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border-color: transparent;
    }
    .none { color: var(--secondary-text-color, #666); }
  `;
__decorate([
    n({ attribute: false })
], ShabbatBlockHeader.prototype, "block", void 0);
__decorate([
    n({ type: Boolean })
], ShabbatBlockHeader.prototype, "enabled", void 0);
__decorate([
    n({ type: Boolean })
], ShabbatBlockHeader.prototype, "dryRun", void 0);
__decorate([
    n({ type: Boolean })
], ShabbatBlockHeader.prototype, "canWrite", void 0);
__decorate([
    n()
], ShabbatBlockHeader.prototype, "masterEntityId", void 0);
__decorate([
    n()
], ShabbatBlockHeader.prototype, "language", void 0);
ShabbatBlockHeader = __decorate([
    t$1('shabbat-block-header')
], ShabbatBlockHeader);

let ShabbatRuleRow = class ShabbatRuleRow extends i {
    constructor() {
        super(...arguments);
        this.defaults = {};
        this.warnings = [];
        this.language = 'en';
    }
    /**
     * The conflict text is rendered inline, not only as a `title=` tooltip.
     * There is no hover on the wall tablet this card is built for, so the
     * tooltip showed nobody anything: the badge said a conflict existed and
     * gave no way to find out what it was. Conflicts are warned and never
     * auto-resolved, so which device and which time clash is the entire
     * actionable content.
     *
     * Always on rather than tap-to-expand: an expander nobody taps is the
     * same silence in a different shape. It costs one short line on the
     * rare row that has a conflict, so the timeline stays scannable.
     *
     * Every conflict, not just the first: `unattachedWarnings` treats a
     * warning as handled the moment it names a displayed rule, so a second
     * conflict on this row that we did not draw would show up nowhere at
     * all - not here and not in the banner.
     */
    render() {
        const conflicts = warningsForRule(this.rule.id, this.warnings);
        const title = this.rule.name;
        return b `
      <div class="row ${this.rule.enabled ? '' : 'disabled'}">
        <span class="dot" style="background:${actionColour(this.rule.action)}"></span>
        <span class="time">${this.rule.time.slice(0, 5)}</span>
        <div class="body">
          ${title ? b `<div class="title">${title}</div>` : A}
          <div class="brief">${ruleBrief(this.rule, this.defaults)}</div>
          ${conflicts.length
            ? b `<div class="conflict-detail">
                ${conflicts.map((conflict) => b `<div>${formatWarning(conflict, this.language)}</div>`)}
              </div>`
            : A}
        </div>
        ${this.rule.enabled
            ? A
            : b `<span class="tag">${t(this.language, 'disabled_rule')}</span>`}
        ${conflicts.length
            ? b `<span
              class="conflict"
              role="img"
              aria-label=${conflicts
                .map((conflict) => formatWarning(conflict, this.language))
                .join('; ')}
              title=${formatWarning(conflicts[0], this.language)}
              >⚠</span
            >`
            : A}
      </div>
    `;
    }
};
ShabbatRuleRow.styles = i$3 `
    .row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding-block: 8px;
      padding-inline: 4px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .row.disabled { opacity: 0.5; }
    .dot { inline-size: 10px; block-size: 10px; border-radius: 50%; flex: none; }
    .time { font-variant-numeric: tabular-nums; min-inline-size: 3.5em; }
    .body { flex: 1; min-inline-size: 0; }
    .title { font-weight: 500; }
    .brief {
      color: var(--secondary-text-color, #666);
      font-size: 0.9em;
      overflow-wrap: anywhere;
    }
    .conflict { color: var(--warning-color, #d9822b); flex: none; }
    /* Inline and always visible - see the note on render(). */
    .conflict-detail {
      color: var(--warning-color, #d9822b);
      font-size: 0.85em;
      overflow-wrap: anywhere;
      margin-block-start: 2px;
    }
    .tag { font-size: 0.8em; color: var(--secondary-text-color, #666); }
  `;
__decorate([
    n({ attribute: false })
], ShabbatRuleRow.prototype, "rule", void 0);
__decorate([
    n({ attribute: false })
], ShabbatRuleRow.prototype, "defaults", void 0);
__decorate([
    n({ attribute: false })
], ShabbatRuleRow.prototype, "warnings", void 0);
__decorate([
    n()
], ShabbatRuleRow.prototype, "language", void 0);
ShabbatRuleRow = __decorate([
    t$1('shabbat-rule-row')
], ShabbatRuleRow);

/**
 * '2026-08-15T20:01:00+03:00' -> '20:01', without a timezone library.
 * Falls back to the raw value when it can't be parsed, so a malformed
 * zmanim timestamp shows up as something visibly wrong next to the
 * marker icon instead of a silent blank.
 */
function clock(iso) {
    const match = /T(\d{2}:\d{2})/.exec(iso);
    return match ? match[1] : iso;
}
let ShabbatDayGroup = class ShabbatDayGroup extends i {
    constructor() {
        super(...arguments);
        this.defaults = {};
        this.warnings = [];
        this.language = 'en';
    }
    label() {
        const { day } = this.group;
        return day === 'erev'
            ? t(this.language, 'erev')
            : `${t(this.language, 'day')} ${day}`;
    }
    render() {
        const { marker, rules } = this.group;
        // Everything lives inside one root element. Under this repo's pinned
        // lit-html@3.3.3 + happy-dom@15.11.7, a render() template with more
        // than one top-level node - even just one static heading <div> beside
        // a single dynamic ternary - fails to render *either* branch of that
        // ternary, not just the not-taken one. The rule this leaves us with:
        // wrap every render() root in a single element, as rule-row.ts already
        // does. This was reproduced under happy-dom only and not confirmed
        // against a real browser, so it's a test-environment constraint we're
        // shaping code around here, not a known lit-html defect in
        // production - Task 12's end-to-end tests run in a real browser and
        // will show whether it matters there.
        return b `
      <div class="day-group">
        <div class="heading">
          <span>${this.label()}</span>
          <span class="date">${this.group.date ?? ''}</span>
        </div>
        ${rules.length
            ? rules.map((rule) => b `
                <shabbat-rule-row
                  .rule=${rule}
                  .defaults=${this.defaults}
                  .warnings=${this.warnings}
                  .language=${this.language}
                ></shabbat-rule-row>
              `)
            : b `<div class="empty">${t(this.language, 'no_rules')}</div>`}
        ${marker
            ? b `
              <div class="marker">
                <span>${marker.kind === 'havdalah' ? '✨' : '🕯️'}</span>
                <span>${t(this.language, marker.kind)}</span>
                <span>${clock(marker.at)}</span>
              </div>
            `
            : A}
      </div>
    `;
    }
};
ShabbatDayGroup.styles = i$3 `
    .heading {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-block: 16px 4px;
      font-weight: 600;
    }
    .date { color: var(--secondary-text-color, #666); font-weight: 400; }
    .empty {
      color: var(--secondary-text-color, #666);
      padding-block: 8px;
      padding-inline: 4px;
      font-size: 0.9em;
    }
    .marker {
      display: flex;
      align-items: center;
      gap: 8px;
      padding-block: 6px;
      padding-inline: 4px;
      color: var(--secondary-text-color, #666);
      font-size: 0.9em;
    }
  `;
__decorate([
    n({ attribute: false })
], ShabbatDayGroup.prototype, "group", void 0);
__decorate([
    n({ attribute: false })
], ShabbatDayGroup.prototype, "defaults", void 0);
__decorate([
    n({ attribute: false })
], ShabbatDayGroup.prototype, "warnings", void 0);
__decorate([
    n()
], ShabbatDayGroup.prototype, "language", void 0);
ShabbatDayGroup = __decorate([
    t$1('shabbat-day-group')
], ShabbatDayGroup);

let ShabbatWarnings = class ShabbatWarnings extends i {
    constructor() {
        super(...arguments);
        this.warnings = [];
        /**
         * The rule ids currently shown on screen (across every visible day
         * group). A warning naming only rules outside this set has nowhere
         * else to appear, so it belongs in the banner - see `unattachedWarnings`.
         *
         * Defaults to `[]` deliberately: over-showing is the safe failure mode.
         * Until a parent passes the real ids, every conflict naming a displayed
         * rule will render twice - once on its row, once in this banner - since
         * none of its rule_ids will ever match this empty set. Task 10 must wire
         * the actual rendered rule ids in for that duplication to go away.
         */
        this.displayedRuleIds = [];
        this.language = 'en';
    }
    render() {
        // Warnings naming a displayed rule are shown on that row instead, so
        // the banner carries only what has nowhere else to go.
        const shown = unattachedWarnings(this.warnings, this.displayedRuleIds);
        if (!shown.length)
            return A;
        return b `
      <div class="banner">
        ${shown.map((warning) => b `<span>${formatWarning(warning, this.language)}</span>`)}
      </div>
    `;
    }
};
ShabbatWarnings.styles = i$3 `
    .banner {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 8px 12px;
      margin-block-end: 8px;
      border-inline-start: 3px solid var(--warning-color, #d9822b);
      background: var(--secondary-background-color, #f4f4f4);
      font-size: 0.9em;
    }
  `;
__decorate([
    n({ attribute: false })
], ShabbatWarnings.prototype, "warnings", void 0);
__decorate([
    n({ attribute: false })
], ShabbatWarnings.prototype, "displayedRuleIds", void 0);
__decorate([
    n()
], ShabbatWarnings.prototype, "language", void 0);
ShabbatWarnings = __decorate([
    t$1('shabbat-warnings')
], ShabbatWarnings);

/** Stamped into the Lovelace resource URL so a rebuild busts the cache. */
const CARD_VERSION = '0.1.0';

/**
 * The only failure the server states as a fact: `ws_subscribe`
 * (websocket_api.py) answers exactly this code when no config entry is
 * loaded. Everything else - a closed socket, a timeout, or core's
 * `unknown_command` because this integration has not registered its
 * command yet during Home Assistant startup - is transient. Calling a
 * transient failure "not configured" is a lie a wall tablet cannot
 * recover from without a page reload, on the one day nobody can operate
 * anything by hand.
 */
const NOT_SET_UP = 'not_set_up';
function isNotSetUp(error) {
    // home-assistant-js-websocket rejects with a plain `{code, message}`
    // object, so `code` is the reliable signal; the `message` fallback is
    // for a thrown Error, which carries no code.
    const code = error?.code;
    if (typeof code === 'string')
        return code === NOT_SET_UP;
    const message = error?.message;
    return typeof message === 'string' && message.includes(NOT_SET_UP);
}
let ShabbatSchedulerCard = class ShabbatSchedulerCard extends i {
    constructor() {
        super(...arguments);
        this._state = null;
        /**
         * `not_set_up` only when the server said so; `stale` when the card
         * could not reach the server at all (a failed subscribe attempt);
         * `command_failed` when it reached the server and the server refused
         * the call. All three leave the last state on screen and nothing else
         * changed, but they are three different things to go and check, and
         * telling someone the connection is lost when it plainly is not sends
         * them to the wrong place.
         */
        this._error = null;
        this._config = {};
        this._unsubscribe = null;
        this._subscribed = false;
        /**
         * Bumped on every detach. An in-flight `_subscribe` compares the value
         * it captured against this one, so a subscription that resolves onto a
         * detached card is torn down instead of being stored where nothing
         * will ever call it. Lovelace moves cards in the DOM on every
         * edit-mode and view switch, so a leak here accumulates for the life
         * of the page.
         */
        this._generation = 0;
        this._onMaster = (event) => {
            const { enabled } = event.detail;
            const entityId = this._state?.master_entity_id;
            if (!entityId)
                return;
            void this._call('switch', enabled ? 'turn_on' : 'turn_off', {
                entity_id: entityId,
            });
        };
        this._onDryRun = (event) => {
            const { dryRun } = event.detail;
            void this._call('shabbat_scheduler', 'set_dry_run', { enabled: dryRun });
        };
    }
    setConfig(config) {
        this._config = config ?? {};
    }
    getCardSize() {
        // The rules actually drawn, not every rule in every profile: a
        // 3-day chag's rules are not on screen during a plain Shabbat.
        return (3 + this._groups.reduce((total, group) => total + group.rules.length, 0));
    }
    static getStubConfig() {
        return { type: 'custom:shabbat-scheduler-card' };
    }
    set hass(hass) {
        // Only a change to something this card renders from is worth a
        // re-render. Home Assistant reassigns `hass` on every state change
        // in the whole system, and re-rendering on each would be its own
        // bug - but never re-rendering means a language switch, or a
        // `hass.user` that was not there at mount, never reaches the view.
        const language = this._language;
        const canWrite = this._canWrite;
        this._hass = hass;
        if (this._language !== language || this._canWrite !== canWrite) {
            this.requestUpdate();
        }
        this._ensureSubscribed();
    }
    get hass() {
        return this._hass;
    }
    /**
     * Subscribe once, and never treat a failure as terminal: `_subscribe`
     * clears `_subscribed` when an attempt fails, so the next `hass`
     * assignment tries again. The flag stays set for the whole in-flight
     * attempt, so a broken server gets one attempt per assignment and
     * never a tight loop.
     */
    _ensureSubscribed() {
        if (this._subscribed || !this._hass || !this.isConnected)
            return;
        this._subscribed = true;
        void this._subscribe();
    }
    async _subscribe() {
        const generation = this._generation;
        try {
            const unsubscribe = await this._hass.connection.subscribeMessage((payload) => {
                if (generation !== this._generation)
                    return;
                this._state = payload;
                this._error = null;
            }, { type: 'shabbat_scheduler/subscribe' });
            if (generation !== this._generation || !this.isConnected) {
                // Detached while this was in flight. The card that asked for
                // this subscription is gone and nothing would ever call this
                // unsubscribe, so call it here.
                void this._teardown(unsubscribe);
                return;
            }
            this._unsubscribe = unsubscribe;
        }
        catch (error) {
            if (generation !== this._generation)
                return;
            this._error = isNotSetUp(error) ? 'not_set_up' : 'stale';
            this._subscribed = false;
        }
    }
    /** Unsubscribing from an already-closed socket is not an error. */
    async _teardown(unsubscribe) {
        if (unsubscribe === null)
            return;
        try {
            await unsubscribe();
        }
        catch {
            // The socket is gone; there is nothing left to unsubscribe from.
        }
    }
    connectedCallback() {
        super.connectedCallback();
        // Re-attached (a view switch, leaving edit mode): subscribe again
        // rather than sit dead until the next `hass` assignment.
        this._ensureSubscribed();
    }
    disconnectedCallback() {
        super.disconnectedCallback();
        this._generation += 1;
        const unsubscribe = this._unsubscribe;
        this._unsubscribe = null;
        this._subscribed = false;
        void this._teardown(unsubscribe);
    }
    get _language() {
        return this._hass?.locale?.language ?? 'en';
    }
    get _canWrite() {
        // 2a made reads open and every mutator require_admin. Offering a
        // control that is certain to fail is worse than not offering it.
        return this._hass?.user?.is_admin === true;
    }
    /**
     * The day groups actually rendered, and `[]` for any payload this card
     * cannot draw. Total on purpose: `render` and `getCardSize` both go
     * through here, and Lovelace calls `getCardSize` while laying a view
     * out, where a throw takes the whole view down with it.
     */
    get _groups() {
        const state = this._state;
        if (state === null || !state.block || !Array.isArray(state.rules))
            return [];
        return buildGroups(state);
    }
    /**
     * A write that fails has to say so. Nothing here is optimistic - the
     * controls only ever show what the server pushed - so a swallowed
     * rejection is a control that visibly does nothing with no
     * explanation, which is this system's cardinal sin. The notice clears
     * itself on the next push, i.e. as soon as a write does land.
     *
     * `command_failed`, not `stale`: reaching this catch means the socket
     * carried the call and the server answered with a rejection - the
     * entity was unavailable, the service errored, permission was refused.
     * Reporting that as "connection lost" is a wrong diagnosis, and on the
     * one day nobody can operate anything by hand it sends the household
     * to check the network instead of the appliance.
     */
    async _call(domain, service, data) {
        try {
            await this._hass.callService(domain, service, data);
        }
        catch {
            this._error = 'command_failed';
        }
    }
    render() {
        // Read once into a local: `_error` is a field, and TypeScript's
        // narrowing of a property access does not survive the intervening
        // calls below, so the notice branch would lose the type that makes
        // it a valid string key.
        const error = this._error;
        if (error === 'not_set_up') {
            return b `
        <ha-card>
          <div class="message">${t(this._language, 'not_set_up')}</div>
        </ha-card>
      `;
        }
        if (this._state === null) {
            return b `
        <ha-card>
          <div class="message">
            ${error === null ? '…' : t(this._language, error)}
          </div>
        </ha-card>
      `;
        }
        const groups = this._groups;
        // The ids of every rule actually rendered on screen right now - only
        // rules matching the block's current profile length, per buildGroups.
        // `unattachedWarnings` (used inside <shabbat-warnings>) needs this
        // exact set: without it, a conflict on a displayed rule would render
        // twice (once on its row, once in the banner), and worse, a conflict
        // naming only rules from another profile would never render at all.
        const displayedRuleIds = groups.flatMap((group) => group.rules.map((rule) => rule.id));
        return b `
      <ha-card>
        ${this._config.title
            ? b `<div class="title">${this._config.title}</div>`
            : A}
        ${error !== null
            ? b `<div class="message notice">${t(this._language, error)}</div>`
            : A}
        <shabbat-block-header
          .block=${this._state.block}
          .enabled=${this._state.enabled}
          .dryRun=${this._state.dry_run}
          .canWrite=${this._canWrite}
          .masterEntityId=${this._state.master_entity_id}
          .language=${this._language}
          @shabbat-master-toggle=${this._onMaster}
          @shabbat-dry-run-toggle=${this._onDryRun}
        ></shabbat-block-header>
        <shabbat-warnings
          .warnings=${this._state.warnings}
          .displayedRuleIds=${displayedRuleIds}
          .language=${this._language}
        ></shabbat-warnings>
        ${groups.map((group) => b `
            <shabbat-day-group
              .group=${group}
              .defaults=${this._state.defaults}
              .warnings=${this._state.warnings}
              .language=${this._language}
            ></shabbat-day-group>
          `)}
      </ha-card>
    `;
    }
};
ShabbatSchedulerCard.styles = i$3 `
    ha-card { padding: 16px; }
    .title { font-size: 1.1em; font-weight: 600; margin-block-end: 8px; }
    .message { color: var(--secondary-text-color, #666); padding-block: 8px; }
    .notice { color: var(--warning-color, #d9822b); }
  `;
__decorate([
    r()
], ShabbatSchedulerCard.prototype, "_state", void 0);
__decorate([
    r()
], ShabbatSchedulerCard.prototype, "_error", void 0);
__decorate([
    n({ attribute: false })
], ShabbatSchedulerCard.prototype, "_config", void 0);
ShabbatSchedulerCard = __decorate([
    t$1('shabbat-scheduler-card')
], ShabbatSchedulerCard);
window.customCards = window.customCards ?? [];
window.customCards.push({
    type: 'shabbat-scheduler-card',
    name: 'Shabbat Scheduler',
    description: 'The coming Shabbat or Chag as a timeline.',
});
console.info(`shabbat-scheduler-card ${CARD_VERSION}`);

export { ShabbatSchedulerCard };
