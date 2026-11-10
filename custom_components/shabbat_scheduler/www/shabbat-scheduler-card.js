function e(e,t,i,n){var o,r=arguments.length,s=r<3?t:null===n?n=Object.getOwnPropertyDescriptor(t,i):n;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)s=Reflect.decorate(e,t,i,n);else for(var a=e.length-1;a>=0;a--)(o=e[a])&&(s=(r<3?o(s):r>3?o(t,i,s):o(t,i))||s);return r>3&&s&&Object.defineProperty(t,i,s),s}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,n=Symbol(),o=new WeakMap;let r=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==n)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=o.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&o.set(t,e))}return e}toString(){return this.cssText}};const s=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,n)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[n+1],e[0]);return new r(i,e,n)},a=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new r("string"==typeof e?e:e+"",void 0,n))(t)})(e):e,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:u,getOwnPropertySymbols:h,getPrototypeOf:p}=Object,g=globalThis,f=g.trustedTypes,_=f?f.emptyScript:"",b=g.reactiveElementPolyfillSupport,m=(e,t)=>e,v={toAttribute(e,t){switch(t){case Boolean:e=e?_:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},y=(e,t)=>!l(e,t),$={attribute:!0,type:String,converter:v,reflect:!1,useDefault:!1,hasChanged:y};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),g.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=$){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),n=this.getPropertyDescriptor(e,i,t);void 0!==n&&c(this.prototype,e,n)}}static getPropertyDescriptor(e,t,i){const{get:n,set:o}=d(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:n,set(t){const r=n?.call(this);o?.call(this,t),this.requestUpdate(e,r,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??$}static _$Ei(){if(this.hasOwnProperty(m("elementProperties")))return;const e=p(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(m("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(m("properties"))){const e=this.properties,t=[...u(e),...h(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(a(e))}else void 0!==e&&t.push(a(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,n)=>{if(i)e.adoptedStyleSheets=n.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of n){const n=document.createElement("style"),o=t.litNonce;void 0!==o&&n.setAttribute("nonce",o),n.textContent=i.cssText,e.appendChild(n)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),n=this.constructor._$Eu(e,i);if(void 0!==n&&!0===i.reflect){const o=(void 0!==i.converter?.toAttribute?i.converter:v).toAttribute(t,i.type);this._$Em=e,null==o?this.removeAttribute(n):this.setAttribute(n,o),this._$Em=null}}_$AK(e,t){const i=this.constructor,n=i._$Eh.get(e);if(void 0!==n&&this._$Em!==n){const e=i.getPropertyOptions(n),o="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:v;this._$Em=n;const r=o.fromAttribute(t,e.type);this[n]=r??this._$Ej?.get(n)??r,this._$Em=null}}requestUpdate(e,t,i,n=!1,o){if(void 0!==e){const r=this.constructor;if(!1===n&&(o=this[e]),i??=r.getPropertyOptions(e),!((i.hasChanged??y)(o,t)||i.useDefault&&i.reflect&&o===this._$Ej?.get(e)&&!this.hasAttribute(r._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:n,wrapped:o},r){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,r??t??this[e]),!0!==o||void 0!==r)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===n&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,n=this[t];!0!==e||this._$AL.has(t)||void 0===n||this.C(t,void 0,i,n)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[m("elementProperties")]=new Map,w[m("finalized")]=new Map,b?.({ReactiveElement:w}),(g.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x=globalThis,k=e=>e,A=x.trustedTypes,C=A?A.createPolicy("lit-html",{createHTML:e=>e}):void 0,S="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,O="?"+E,T=`<${O}>`,I=document,N=()=>I.createComment(""),j=e=>null===e||"object"!=typeof e&&"function"!=typeof e,M=Array.isArray,R="[ \t\n\f\r]",P=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,z=/-->/g,D=/>/g,W=RegExp(`>|${R}(?:([^\\s"'>=/]+)(${R}*=${R}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),L=/'/g,F=/"/g,U=/^(?:script|style|textarea|title)$/i,B=(e=>(t,...i)=>({_$litType$:e,strings:t,values:i}))(1),H=Symbol.for("lit-noChange"),q=Symbol.for("lit-nothing"),Y=new WeakMap,K=I.createTreeWalker(I,129);function V(e,t){if(!M(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==C?C.createHTML(t):t}const G=(e,t)=>{const i=e.length-1,n=[];let o,r=2===t?"<svg>":3===t?"<math>":"",s=P;for(let t=0;t<i;t++){const i=e[t];let a,l,c=-1,d=0;for(;d<i.length&&(s.lastIndex=d,l=s.exec(i),null!==l);)d=s.lastIndex,s===P?"!--"===l[1]?s=z:void 0!==l[1]?s=D:void 0!==l[2]?(U.test(l[2])&&(o=RegExp("</"+l[2],"g")),s=W):void 0!==l[3]&&(s=W):s===W?">"===l[0]?(s=o??P,c=-1):void 0===l[1]?c=-2:(c=s.lastIndex-l[2].length,a=l[1],s=void 0===l[3]?W:'"'===l[3]?F:L):s===F||s===L?s=W:s===z||s===D?s=P:(s=W,o=void 0);const u=s===W&&e[t+1].startsWith("/>")?" ":"";r+=s===P?i+T:c>=0?(n.push(a),i.slice(0,c)+S+i.slice(c)+E+u):i+E+(-2===c?t:u)}return[V(e,r+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),n]};class J{constructor({strings:e,_$litType$:t},i){let n;this.parts=[];let o=0,r=0;const s=e.length-1,a=this.parts,[l,c]=G(e,t);if(this.el=J.createElement(l,i),K.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(n=K.nextNode())&&a.length<s;){if(1===n.nodeType){if(n.hasAttributes())for(const e of n.getAttributeNames())if(e.endsWith(S)){const t=c[r++],i=n.getAttribute(e).split(E),s=/([.?@])?(.*)/.exec(t);a.push({type:1,index:o,name:s[2],strings:i,ctor:"."===s[1]?te:"?"===s[1]?ie:"@"===s[1]?ne:ee}),n.removeAttribute(e)}else e.startsWith(E)&&(a.push({type:6,index:o}),n.removeAttribute(e));if(U.test(n.tagName)){const e=n.textContent.split(E),t=e.length-1;if(t>0){n.textContent=A?A.emptyScript:"";for(let i=0;i<t;i++)n.append(e[i],N()),K.nextNode(),a.push({type:2,index:++o});n.append(e[t],N())}}}else if(8===n.nodeType)if(n.data===O)a.push({type:2,index:o});else{let e=-1;for(;-1!==(e=n.data.indexOf(E,e+1));)a.push({type:7,index:o}),e+=E.length-1}o++}}static createElement(e,t){const i=I.createElement("template");return i.innerHTML=e,i}}function Z(e,t,i=e,n){if(t===H)return t;let o=void 0!==n?i._$Co?.[n]:i._$Cl;const r=j(t)?void 0:t._$litDirective$;return o?.constructor!==r&&(o?._$AO?.(!1),void 0===r?o=void 0:(o=new r(e),o._$AT(e,i,n)),void 0!==n?(i._$Co??=[])[n]=o:i._$Cl=o),void 0!==o&&(t=Z(e,o._$AS(e,t.values),o,n)),t}class Q{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,n=(e?.creationScope??I).importNode(t,!0);K.currentNode=n;let o=K.nextNode(),r=0,s=0,a=i[0];for(;void 0!==a;){if(r===a.index){let t;2===a.type?t=new X(o,o.nextSibling,this,e):1===a.type?t=new a.ctor(o,a.name,a.strings,this,e):6===a.type&&(t=new oe(o,this,e)),this._$AV.push(t),a=i[++s]}r!==a?.index&&(o=K.nextNode(),r++)}return K.currentNode=I,n}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class X{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,n){this.type=2,this._$AH=q,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=Z(this,e,t),j(e)?e===q||null==e||""===e?(this._$AH!==q&&this._$AR(),this._$AH=q):e!==this._$AH&&e!==H&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>M(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==q&&j(this._$AH)?this._$AA.nextSibling.data=e:this.T(I.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,n="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=J.createElement(V(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===n)this._$AH.p(t);else{const e=new Q(n,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=Y.get(e.strings);return void 0===t&&Y.set(e.strings,t=new J(e)),t}k(e){M(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,n=0;for(const o of e)n===t.length?t.push(i=new X(this.O(N()),this.O(N()),this,this.options)):i=t[n],i._$AI(o),n++;n<t.length&&(this._$AR(i&&i._$AB.nextSibling,n),t.length=n)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ee{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,n,o){this.type=1,this._$AH=q,this._$AN=void 0,this.element=e,this.name=t,this._$AM=n,this.options=o,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=q}_$AI(e,t=this,i,n){const o=this.strings;let r=!1;if(void 0===o)e=Z(this,e,t,0),r=!j(e)||e!==this._$AH&&e!==H,r&&(this._$AH=e);else{const n=e;let s,a;for(e=o[0],s=0;s<o.length-1;s++)a=Z(this,n[i+s],t,s),a===H&&(a=this._$AH[s]),r||=!j(a)||a!==this._$AH[s],a===q?e=q:e!==q&&(e+=(a??"")+o[s+1]),this._$AH[s]=a}r&&!n&&this.j(e)}j(e){e===q?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class te extends ee{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===q?void 0:e}}class ie extends ee{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==q)}}class ne extends ee{constructor(e,t,i,n,o){super(e,t,i,n,o),this.type=5}_$AI(e,t=this){if((e=Z(this,e,t,0)??q)===H)return;const i=this._$AH,n=e===q&&i!==q||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,o=e!==q&&(i===q||n);n&&this.element.removeEventListener(this.name,this,i),o&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class oe{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){Z(this,e)}}const re=x.litHtmlPolyfillSupport;re?.(J,X),(x.litHtmlVersions??=[]).push("3.3.3");const se=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */let ae=class extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const n=i?.renderBefore??t;let o=n._$litPart$;if(void 0===o){const e=i?.renderBefore??null;n._$litPart$=o=new X(t.insertBefore(N(),e),e,void 0,i??{})}return o._$AI(e),o})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return H}};ae._$litElement$=!0,ae.finalized=!0,se.litElementHydrateSupport?.({LitElement:ae});const le=se.litElementPolyfillSupport;le?.({LitElement:ae}),(se.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ce=e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},de={attribute:!0,type:String,converter:v,reflect:!1,hasChanged:y},ue=(e=de,t,i)=>{const{kind:n,metadata:o}=i;let r=globalThis.litPropertyMetadata.get(o);if(void 0===r&&globalThis.litPropertyMetadata.set(o,r=new Map),"setter"===n&&((e=Object.create(e)).wrapped=!0),r.set(i.name,e),"accessor"===n){const{name:n}=i;return{set(i){const o=t.get.call(this);t.set.call(this,i),this.requestUpdate(n,o,e,!0,i)},init(t){return void 0!==t&&this.C(n,void 0,e,t),t}}}if("setter"===n){const{name:n}=i;return function(i){const o=this[n];t.call(this,i),this.requestUpdate(n,o,e,!0,i)}}throw Error("Unsupported decorator location: "+n)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function he(e){return(t,i)=>"object"==typeof i?ue(e,t,i):((e,t,i)=>{const n=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),n?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pe(e){return he({...e,state:!0,attribute:!1})}const ge={en:{erev:"Erev",day:"Day",candle_lighting:"Candle lighting",havdalah:"Havdalah",master:"Shabbat Scheduler",no_block:"No upcoming Shabbat could be derived from the Jewish Calendar sensors.",not_set_up:"Shabbat Scheduler is not configured.",stale:"Connection lost — showing the last known state.",command_failed:"That did not go through. Nothing was changed.",no_rules:"No rules for this block.",disabled_rule:"disabled",conflict_prefix:"Conflict",edit_rule:"Edit rule",add_rule:"Add rule",time:"Time",name:"Name",enabled:"Enabled",advanced:"Advanced",icon:"Icon",colour:"Colour",save:"Save",cancel:"Cancel",delete_rule:"Delete",duplicate:"Duplicate",read_only:"You do not have permission to change the schedule.",will_conflict:"This overlaps another rule. You can still save it — nothing is resolved for you.",defaults_title:"Shared defaults",defaults_help:"Rules inherit these unless they set their own.",card_language:"Card language",card_language_auto:"Auto (match Home Assistant)",target:"Target",data:"Data",preview_banner:"Preview — not the coming Shabbat. Dates are not shown because this block is not scheduled.",inherits_target_from_defaults:"Inherited from the shared defaults:",target_none:"No target — this rule will not reach anything.",replay_after_restart:"Replay after a restart",replay_within_label:"Only if less than",replay_help:"Off by default: after a restart, nothing that already passed is re-run.",conditions:"Conditions",conditions_help:"All conditions must pass, or the rule does not run and says why.",add_condition:"Add condition",remove_condition:"Remove",condition_unparseable:"Not valid YAML — this condition is not being saved.",condition_not_a_mapping:"A condition must be a mapping, like `condition: state`.",outcome_called:"Fired",outcome_would_call:"Would have fired [dry run]",outcome_failed:"Did not run — failed",outcome_blocked:"Did not run — blocked",outcome_skipped_stale:"Did not run — skipped as stale",outcome_skipped_no_replay:"Did not run — was due after a restart, replay is off",outcome_skipped_superseded:"Did not run — a later rule for the same device replaced it",outcome_unknown:"Finished with no reported outcome",outcome_no_such_entity:"no such entity: ",outcome_reached_nothing:"reached no entity that exists",outcome_invalid_data:"would be refused: ",run_now_button:"Run now",run_now_simulate:"Simulate",run_now_real:"Run for real",run_now_disabled_dirty:"Save your changes first",simulate_title:"Test your schedule",simulate_profile:"Block length",simulate_day:"Day",simulate_force_conditions:"Force conditions to pass",simulate_this_day:"Simulate this day",simulate_run_for_real:"Run this day for real",simulate_run_for_real_confirm:"This will actually operate your devices, in order, for",clone_day_prefix:"Clone day",clone_profile_prefix:"Clone the",clone_profile_suffix:"-day profile",clone_target_profile:"Target block length",clone_target_day:"Target day",clone_extend:"Extend",clone_overwrite:"Overwrite",clone_target_has_rules:"The target has existing rule(s):",clone_confirm:"Clone",clone_landed:"Cloned",clone_failed:"Not cloned",clone_none:"none",section_action:"Action",section_conditions:"Only if",section_options:"Options"},he:{erev:"ערב",day:"יום",candle_lighting:"הדלקת נרות",havdalah:"הבדלה",master:"שעון שבת",no_block:"לא ניתן לגזור שבת קרובה מחיישני לוח השנה העברי.",not_set_up:"שעון שבת אינו מוגדר.",stale:"החיבור אבד — מוצג המצב האחרון הידוע.",command_failed:"הפעולה לא בוצעה. שום דבר לא השתנה.",no_rules:"אין כללים לבלוק הזה.",disabled_rule:"מושבת",conflict_prefix:"התנגשות",edit_rule:"עריכת כלל",add_rule:"הוספת כלל",time:"שעה",name:"שם",enabled:"מופעל",advanced:"מתקדם",icon:"סמל",colour:"צבע",save:"שמירה",cancel:"ביטול",delete_rule:"מחיקה",duplicate:"שכפול",read_only:"אין לך הרשאה לשנות את הלוח.",will_conflict:"הכלל חופף לכלל אחר. אפשר לשמור בכל זאת — שום דבר לא ייפתר עבורך.",defaults_title:"ברירות מחדל משותפות",defaults_help:"כללים יורשים אותן אלא אם הגדירו משלהם.",card_language:"שפת הכרטיס",card_language_auto:"אוטומטי (כמו Home Assistant)",target:"יעד",data:"נתונים",preview_banner:"תצוגה מקדימה — לא השבת הקרובה. התאריכים אינם מוצגים כי הבלוק הזה אינו מתוכנן.",inherits_target_from_defaults:"נורש מברירת המחדל המשותפת:",target_none:"ללא יעד — הכלל לא יפעל על שום דבר.",replay_after_restart:"הפעלה חוזרת לאחר אתחול",replay_within_label:"רק אם עברו פחות מ־",replay_help:"כברירת מחדל כבוי: לאחר אתחול, מה שכבר עבר לא יופעל שוב.",conditions:"תנאים",conditions_help:"כל התנאים חייבים להתקיים, אחרת הכלל לא ירוץ ויציין זאת.",add_condition:"הוספת תנאי",remove_condition:"הסרה",condition_unparseable:"YAML לא תקין — התנאי הזה לא נשמר.",condition_not_a_mapping:"תנאי חייב להיות מפה, כמו `condition: state`.",outcome_called:"הופעל",outcome_would_call:"היה מופעל [הרצה יבשה]",outcome_failed:"לא רץ — נכשל",outcome_blocked:"לא רץ — נחסם",outcome_skipped_stale:"לא רץ — דולג כמיושן",outcome_skipped_no_replay:"לא רץ — היה אמור לרוץ לאחר אתחול, הפעלה חוזרת כבויה",outcome_skipped_superseded:"לא רץ — כלל מאוחר יותר לאותו מכשיר החליף אותו",outcome_unknown:"הסתיים ללא תוצאה מדווחת",outcome_no_such_entity:"אין ישות כזו: ",outcome_reached_nothing:"לא הגיע לאף ישות קיימת",outcome_invalid_data:"היה נדחה: ",run_now_button:"הרצה עכשיו",run_now_simulate:"סימולציה",run_now_real:"הרצה אמיתית",run_now_disabled_dirty:"שמור/י את השינויים תחילה",simulate_title:"בדיקת הלוח",simulate_profile:"אורך הבלוק",simulate_day:"יום",simulate_force_conditions:"לעקוף תנאים",simulate_this_day:"סימולציה ליום זה",simulate_run_for_real:"הרצה אמיתית ליום זה",simulate_run_for_real_confirm:"פעולה זו תפעיל בפועל את המכשירים שלך, בסדר, עבור",clone_day_prefix:"שכפול יום",clone_profile_prefix:"שכפול פרופיל בן",clone_profile_suffix:"ימים",clone_target_profile:"אורך היעד",clone_target_day:"יום היעד",clone_extend:"הוספה",clone_overwrite:"החלפה",clone_target_has_rules:"ליעד כבר יש כללים:",clone_confirm:"שכפול",clone_landed:"שוכפלו",clone_failed:"לא שוכפלו",clone_none:"ללא",section_action:"פעולה",section_conditions:"רק אם",section_options:"אפשרויות"}};function fe(e,t){return("he"===e?ge.he:ge.en)[t]}function _e(e){return"erev"===e?-1:Number(e)}function be(e){const t=["erev"];for(let i=1;i<=e;i+=1)t.push(String(i));return t}function me(e){return function(e){return be(e.length)}(e).map(t=>e.dates[t]).filter(e=>void 0!==e)}function ve(e,t){return null===e.block||e.block.length!==t}const ye={entity_id:(e,t)=>{const i=t?.states?.[e]?.attributes.friendly_name;return"string"==typeof i&&""!==i?i:e},area_id:(e,t)=>t?.areas?.[e]?.name??e,device_id:(e,t)=>{const i=t?.devices?.[e];return i?.name_by_user||i?.name||e},label_id:(e,t)=>t?.labels?.[e]?.name??e,floor_id:(e,t)=>t?.floors?.[e]?.name??e};function $e(e,t=null){const i=[];for(const[n,o]of Object.entries(e)){const e=ye[n]??(e=>e);Array.isArray(o)?i.push(...o.map(i=>e(String(i),t))):null!=o&&i.push(e(String(o),t))}return i.join(", ")}function we(e,t){return"erev"===e?fe(t,"erev"):`${fe(t,"day")} ${e}`}function xe(e,t){if("conflict"===e.kind&&void 0!==e.targets&&e.targets.length>0&&void 0!==e.time){const i=[fe(t,"conflict_prefix"),e.targets.join(", ")];return void 0!==e.day&&i.push(we(e.day,t)),i.push(e.time),i.join(" · ")}return e.message??""}const ke={called:"outcome_called",would_call:"outcome_would_call",failed:"outcome_failed",blocked:"outcome_blocked",skipped_stale:"outcome_skipped_stale",skipped_no_replay:"outcome_skipped_no_replay",skipped_superseded:"outcome_skipped_superseded"};function Ae(e,t){let i=fe(t,ke[e.outcome]??"outcome_unknown");e.detail&&(i=`${i}: ${e.detail}`);const n=e.unknown_targets??[];n.length>0&&!i.includes("no such entity: ")&&(i=`${i} — ${fe(t,"outcome_no_such_entity")}${n.join(", ")}`),!0===e.no_live_targets&&(i=`${i} — ${fe(t,"outcome_reached_nothing")}`);const o=(e.wrong_targets??[]).filter(e=>!i.includes(e));o.length>0&&(i=`${i} — ${o.join("; ")}`);const r=e.invalid_data??[];return r.length>0&&(i=`${i} — ${fe(t,"outcome_invalid_data")}${r.join("; ")}`),i}const Ce=["failed","blocked","skipped_stale","skipped_no_replay","skipped_superseded","would_call","called"];function Se(e,t){if(0===e.length)return{outcome:"unknown",at:t,detail:null};const i=new Set(e.map(e=>String(e.outcome??""))),n=Ce.find(e=>i.has(e))??"unknown",o=e.find(e=>e.outcome===n&&(e.error||e.reason)),r=Array.from(new Set(e.flatMap(e=>e.unknown_targets??[]))),s=Array.from(new Set(e.flatMap(e=>e.invalid_data??[]))),a=Array.from(new Set(e.flatMap(e=>e.wrong_targets??[])));return{outcome:n,at:t,detail:o?.error??o?.reason??null,unknown_targets:r.length?r:void 0,no_live_targets:e.some(e=>!0===e.no_live_targets)||void 0,invalid_data:s.length?s:void 0,wrong_targets:a.length?a:void 0}}const Ee=["day","time","action","target","data","condition","replay","name","icon","color","enabled"];function Oe(e,t){return{...e,profile:t}}function Te(e,t){const i={};for(const n of Ee){const o=e[n],r=t[n];JSON.stringify(o)!==JSON.stringify(r)&&(i[n]=o)}return i}let Ie=class extends ae{constructor(){super(...arguments),this.hass=null,this.block=null,this.enabled=!1,this.canWrite=!1,this.masterEntityId=null,this.language="en",this.selectedProfile=1,this._onMasterChanged=e=>{this.dispatchEvent(new CustomEvent("shabbat-master-toggle",{detail:{enabled:Boolean(e.detail?.value)}}))}}_dates(){if(null===this.block)return q;return me(this.block).map((e,t)=>B`<span>${t>0?" → ":""}<span class="date">${e}</span></span>`)}render(){return B`
      <div class="header">
        <div class="label">
          ${null===this.block?B`<span class="none">${fe(this.language,"no_block")}</span>`:B`
                <span>${fe(this.language,"day")} ×${this.block.length}</span>
                <span class="dates">${this._dates()}</span>
              `}
        </div>
        <div class="chips">
          ${[1,2,3].map(e=>B`
              <button
                class="chip ${this.selectedProfile===e?"active":""}"
                @click=${()=>this.dispatchEvent(new CustomEvent("profile-selected",{detail:{profile:e}}))}
              >
                ${e}d
              </button>
            `)}
          ${this.canWrite?B`<button
                class="clone-menu"
                aria-label=${fe(this.language,"clone_profile_prefix")}
                @click=${()=>this.dispatchEvent(new CustomEvent("clone-open",{detail:{scope:"profile",profile:this.selectedProfile},bubbles:!0,composed:!0}))}
              >⋮</button>`:q}
        </div>
        ${this.canWrite?B`<button
              class="gear"
              @click=${()=>this.dispatchEvent(new CustomEvent("defaults-open"))}
            >
              ⚙
            </button>`:q}
        ${this.canWrite?B`<button
              class="simulate-open"
              aria-label=${fe(this.language,"simulate_title")}
              @click=${()=>this.dispatchEvent(new CustomEvent("simulate-open",{bubbles:!0,composed:!0}))}
            >
              ▶
            </button>`:q}
        <div class="master-wrap">
          <span class="master-label">${fe(this.language,"master")}</span>
          <ha-selector
            class="master"
            .hass=${this.hass}
            .selector=${{boolean:{}}}
            .value=${this.enabled}
            .disabled=${!this.canWrite||null===this.masterEntityId}
            @value-changed=${this._onMasterChanged}
          ></ha-selector>
        </div>
      </div>
    `}};var Ne;Ie.styles=s`
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      padding-block-end: 8px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .label {
      flex: 1;
      min-inline-size: 0;
      font-weight: 600;
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      column-gap: 8px;
    }
    /* The title ("Day ×1") is one unbreakable unit; .dates wraps normally
       (at the arrow, between dates) but each individual .date span does
       not, so a narrow header wraps at a sensible point instead of
       breaking a date's own digits across two lines - hyphens in
       "2026-08-14" are otherwise a normal CSS soft-wrap point, which is
       what used to split it into "2026-08-" and "14". */
    .label > span:first-child { white-space: nowrap; }
    .dates .date { white-space: nowrap; }
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
    .none { color: var(--secondary-text-color, #666); }
    .chips { display: flex; gap: 4px; }
    .chip {
      font: inherit;
      font-size: 0.85em;
      padding-block: 2px;
      padding-inline: 8px;
      border-radius: 10px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    .chip.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border-color: transparent;
    }
    .gear, .simulate-open { border: none; background: none; cursor: pointer; font-size: 1.1em; }
    .clone-menu { font: inherit; background: none; border: none; cursor: pointer; font-size: 1.1em; }
    .master-wrap { display: flex; align-items: center; gap: 6px; }
    .master-label { font-size: 0.9em; }
    @media (max-width: 599px) {
      .header { flex-wrap: wrap; }
      .label { flex-basis: 100%; }
      .chips, .gear, .master, button {
        min-block-size: 44px;
      }
      .chip { min-block-size: 44px; display: inline-flex; align-items: center; }
    }
  `,e([he({attribute:!1})],Ie.prototype,"hass",void 0),e([he({attribute:!1})],Ie.prototype,"block",void 0),e([he({type:Boolean})],Ie.prototype,"enabled",void 0),e([he({type:Boolean})],Ie.prototype,"canWrite",void 0),e([he()],Ie.prototype,"masterEntityId",void 0),e([he()],Ie.prototype,"language",void 0),e([he({type:Number})],Ie.prototype,"selectedProfile",void 0),Ie=e([ce("shabbat-block-header")],Ie);let je=Ne=class extends ae{constructor(){super(...arguments),this.hass=null,this.defaults={},this.warnings=[],this.canWrite=!1,this.toggleError=null,this.language="en",this._menu=null,this._pressTimer=null,this._pressStart=null,this._suppressClick=!1}disconnectedCallback(){super.disconnectedCallback(),this._cancelPress()}_openMenu(e,t){if(!this.canWrite)return;const i=Math.max(0,window.innerWidth-180),n=Math.max(0,window.innerHeight-110);this._menu={x:Math.min(e,i),y:Math.min(t,n)}}_closeMenu(){this._menu=null}_cancelPress(){null!==this._pressTimer&&clearTimeout(this._pressTimer),this._pressTimer=null,this._pressStart=null}_onPointerDown(e){this.canWrite&&"mouse"!==e.pointerType&&(this._cancelPress(),this._pressStart={x:e.clientX,y:e.clientY},this._pressTimer=setTimeout(()=>{const e=this._pressStart;this._pressTimer=null,null!==e&&(this._suppressClick=!0,this._openMenu(e.x,e.y))},Ne.LONG_PRESS_MS))}_onPointerMove(e){const t=this._pressStart;null!==t&&(Math.abs(e.clientX-t.x)>10||Math.abs(e.clientY-t.y)>10)&&this._cancelPress()}_onContextMenu(e){this.canWrite&&(e.preventDefault(),this._cancelPress(),this._openMenu(e.clientX,e.clientY))}_onRowClick(){this._suppressClick?this._suppressClick=!1:this._open()}_delete(){this._closeMenu(),this.dispatchEvent(new CustomEvent("rule-delete",{detail:{rule:this.rule},bubbles:!0,composed:!0}))}_renderMenu(){return null===this._menu?q:B`<div class="menu-layer">
      <div
        class="menu-backdrop"
        @click=${e=>{e.stopPropagation(),this._closeMenu()}}
        @contextmenu=${e=>{e.preventDefault(),this._closeMenu()}}
      ></div>
      <div
        class="menu"
        role="menu"
        style="left:${this._menu.x}px;top:${this._menu.y}px"
      >
        <button
          class="menu-edit"
          role="menuitem"
          @click=${e=>{e.stopPropagation(),this._closeMenu(),this._open()}}
        >${fe(this.language,"edit_rule")}</button>
        <button
          class="menu-delete"
          role="menuitem"
          @click=${e=>{e.stopPropagation(),this._delete()}}
        >${fe(this.language,"delete_rule")}</button>
      </div>
    </div>`}_open(){this.dispatchEvent(new CustomEvent("rule-open",{detail:{rule:this.rule},bubbles:!0,composed:!0}))}render(){const e=(t=this.rule.id,this.warnings.filter(e=>e.rule_ids?.includes(t)));var t;const i=this.rule.name,n=this.rule.last_outcome??null,o=null===n?"":function(e,t){const i=new Date(e);return Number.isNaN(i.getTime())?"":i.toLocaleString("he"===t?"he-IL":"en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}(n.at,this.language);return B`
      <div class="row-wrap">
      <div
        class="row ${this.rule.enabled?"":"disabled"}"
        tabindex="0"
        role="button"
        @click=${()=>this._onRowClick()}
        @contextmenu=${e=>this._onContextMenu(e)}
        @pointerdown=${e=>this._onPointerDown(e)}
        @pointermove=${e=>this._onPointerMove(e)}
        @pointerup=${()=>this._cancelPress()}
        @pointercancel=${()=>this._cancelPress()}
        @pointerleave=${()=>this._cancelPress()}
        @keydown=${e=>{if("Enter"===e.key||" "===e.key)e.preventDefault(),this._open();else if("ContextMenu"===e.key||e.shiftKey&&"F10"===e.key){e.preventDefault();const t=e.currentTarget.getBoundingClientRect();this._openMenu(t.left+16,t.top+t.height/2)}}}
      >
        ${this.canWrite?B`<ha-selector
              class="row-toggle"
              .hass=${this.hass}
              .selector=${{boolean:{}}}
              .value=${this.rule.enabled}
              @click=${e=>e.stopPropagation()}
              @keydown=${e=>e.stopPropagation()}
              @value-changed=${()=>{this.dispatchEvent(new CustomEvent("rule-toggle-enabled",{detail:{rule:this.rule},bubbles:!0,composed:!0}))}}
            ></ha-selector>`:q}
        <span class="dot" style="background:${r=this.rule,r.color??"var(--secondary-text-color, #888)"}"></span>
        <span class="time">${this.rule.time.slice(0,5)}</span>
        <div class="body">
          ${i?B`<div class="title">${i}</div>`:q}
          <div class="brief ${i?"":"promoted"}">
            ${function(e,t,i=null){const n=Object.keys(e.target).length?e.target:t.target??{},o={...t.data??{},...e.data},r=[e.action,$e(n,i)];for(const e of Object.values(o))null!=e&&r.push(String(e));return r.filter(e=>""!==e).join(" · ")}(this.rule,this.defaults,this.hass)}
          </div>
          ${null!==this.toggleError?B`<div class="row-error">${this.toggleError}</div>`:q}
          ${null!==n?B`<div class="last-outcome ${function(e){return"failed"===e.outcome||"blocked"===e.outcome||"skipped_stale"===e.outcome||(e.unknown_targets??[]).length>0||!0===e.no_live_targets||(e.wrong_targets??[]).length>0||(e.invalid_data??[]).length>0||!(e.outcome in ke)}(n)?"bad":""}">
                <span>${Ae(n,this.language)}</span>
                ${o?B`<span class="last-outcome-at">${o}</span>`:q}
              </div>`:q}
          ${e.length?B`<div class="conflict-detail">
                ${e.map(e=>B`<div>${xe(e,this.language)}</div>`)}
              </div>`:q}
        </div>
        ${this.rule.enabled?q:B`<span class="tag">${fe(this.language,"disabled_rule")}</span>`}
        ${e.length?B`<span
              class="conflict"
              role="img"
              aria-label=${e.map(e=>xe(e,this.language)).join("; ")}
              title=${xe(e[0],this.language)}
              >⚠</span
            >`:q}
      </div>
      ${this._renderMenu()}
      </div>
    `;var r}};je.LONG_PRESS_MS=500,je.styles=s`
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
    /* A rule with no name has no .title to caption, so .brief takes
       over its exact look instead of staying a small, grey second line
       with nothing above it to be second TO. Same text either way -
       only a rule's own name changes which class it renders in. */
    .brief.promoted {
      color: inherit;
      font-size: 1em;
      font-weight: 500;
    }
    .conflict { color: var(--warning-color, #d9822b); flex: none; }
    /* Inline and always visible - see the note on render(). */
    .conflict-detail {
      color: var(--warning-color, #d9822b);
      font-size: 0.85em;
      overflow-wrap: anywhere;
      margin-block-start: 2px;
    }
    /* Inline and always visible, for the same reason .conflict-detail is:
       there is no hover on the wall tablet this card is built for, so a
       tooltip would show nobody anything. */
    .last-outcome {
      font-size: 0.85em;
      color: var(--secondary-text-color, #666);
      overflow-wrap: anywhere;
      margin-block-start: 2px;
    }
    /* Not red: a rule that did not run is not an error in the card, and
       the conflict warning colour is already taken. Distinct enough to
       find while scanning, quiet enough not to shout on every row. */
    .last-outcome.bad { color: var(--error-color, #c62828); }
    .last-outcome-at { opacity: 0.8; margin-inline-start: 0.5em; }
    .tag { font-size: 0.8em; color: var(--secondary-text-color, #666); }
    .row-toggle { flex: none; }
    .row-error {
      color: var(--error-color, #c62828);
      font-size: 0.85em;
      overflow-wrap: anywhere;
      margin-block-start: 2px;
    }
    .row { cursor: pointer; }
    .row:focus-visible { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: -2px; }
    /* Below 600px, .body's children (title, brief, last-outcome,
       conflict-detail) become direct flex items of .row via
       display: contents - the same unwrap trick rule-dialog.ts's
       .advanced class already uses, for the same reason: only that lets
       .title stay on the row's first line, next to the dot and time,
       while .brief/.last-outcome/.conflict-detail wrap onto their
       own full-width lines below. .body itself has no visual box (no
       padding/border/background), so nothing is lost by unwrapping it. */
    /* A long press on a touch screen must open OUR menu, not select the
       row's text or pop the browser's own callout. */
    .row { -webkit-touch-callout: none; user-select: none; -webkit-user-select: none; }
    .menu-backdrop { position: fixed; inset: 0; z-index: 9; }
    .menu {
      position: fixed;
      z-index: 10;
      min-inline-size: 9em;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
      padding-block: 4px;
    }
    .menu button {
      display: block;
      inline-size: 100%;
      font: inherit;
      text-align: start;
      background: none;
      border: none;
      color: inherit;
      padding-block: 10px;
      padding-inline: 16px;
      cursor: pointer;
    }
    .menu button:hover { background: var(--secondary-background-color, #f4f4f4); }
    .menu .menu-delete { color: var(--error-color, #c62828); }
    @media (max-width: 599px) {
      .row { flex-wrap: wrap; row-gap: 4px; }
      .body { display: contents; }
      .brief, .last-outcome, .conflict-detail { flex-basis: 100%; }
    }
  `,e([he({attribute:!1})],je.prototype,"hass",void 0),e([he({attribute:!1})],je.prototype,"rule",void 0),e([he({attribute:!1})],je.prototype,"defaults",void 0),e([he({attribute:!1})],je.prototype,"warnings",void 0),e([he({type:Boolean})],je.prototype,"canWrite",void 0),e([he()],je.prototype,"toggleError",void 0),e([he()],je.prototype,"language",void 0),e([pe()],je.prototype,"_menu",void 0),je=Ne=e([ce("shabbat-rule-row")],je);let Me=class extends ae{constructor(){super(...arguments),this.hass=null,this.defaults={},this.warnings=[],this.language="en",this.canWrite=!1,this.profile=1,this.toggleErrors={}}label(){const{day:e}=this.group;return"erev"===e?fe(this.language,"erev"):`${fe(this.language,"day")} ${e}`}render(){const{marker:e,rules:t}=this.group;return B`
      <div class="day-group">
        <div class="heading">
          <span>${this.label()}</span>
          <span class="date">${this.group.date??""}</span>
          ${this.canWrite?B`<button
                class="clone-menu"
                aria-label=${fe(this.language,"clone_day_prefix")}
                @click=${()=>this.dispatchEvent(new CustomEvent("clone-open",{detail:{scope:"day",profile:this.profile,day:this.group.day},bubbles:!0,composed:!0}))}
              >⋮</button>`:q}
        </div>
        ${t.length?t.map(e=>B`
                <shabbat-rule-row
                  .hass=${this.hass}
                  .rule=${e}
                  .defaults=${this.defaults}
                  .warnings=${this.warnings}
                  .language=${this.language}
                  .canWrite=${this.canWrite}
                  .toggleError=${this.toggleErrors[e.id]??null}
                ></shabbat-rule-row>
              `):B`<div class="empty">${fe(this.language,"no_rules")}</div>`}
        ${this.canWrite?B`<button
              class="add"
              @click=${()=>this.dispatchEvent(new CustomEvent("rule-add",{detail:{day:this.group.day}}))}
            >
              + ${fe(this.language,"add_rule")}
            </button>`:q}
        ${e?B`
              <div class="marker">
                <span>${"havdalah"===e.kind?"✨":"🕯️"}</span>
                <span>${fe(this.language,e.kind)}</span>
                <span>${function(e){const t=/T(\d{2}:\d{2})/.exec(e);return t?t[1]:e}(e.at)}</span>
              </div>
            `:q}
      </div>
    `}};Me.styles=s`
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
    .add {
      font: inherit;
      font-size: 0.9em;
      background: none;
      border: none;
      color: var(--primary-color, #03a9f4);
      padding-block: 6px;
      padding-inline: 4px;
      cursor: pointer;
    }
    .clone-menu {
      font: inherit; background: none; border: none; cursor: pointer;
      font-size: 1.1em; margin-inline-start: auto; padding-inline: 4px;
    }
  `,e([he({attribute:!1})],Me.prototype,"hass",void 0),e([he({attribute:!1})],Me.prototype,"group",void 0),e([he({attribute:!1})],Me.prototype,"defaults",void 0),e([he({attribute:!1})],Me.prototype,"warnings",void 0),e([he()],Me.prototype,"language",void 0),e([he({type:Boolean})],Me.prototype,"canWrite",void 0),e([he({type:Number})],Me.prototype,"profile",void 0),e([he({attribute:!1})],Me.prototype,"toggleErrors",void 0),Me=e([ce("shabbat-day-group")],Me);let Re=class extends ae{constructor(){super(...arguments),this.warnings=[],this.displayedRuleIds=[],this.language="en"}render(){const e=function(e,t){const i=new Set(t);return e.filter(e=>!e.rule_ids?.some(e=>i.has(e)))}(this.warnings,this.displayedRuleIds);return e.length?B`
      <div class="banner">
        ${e.map(e=>B`<span>${xe(e,this.language)}</span>`)}
      </div>
    `:q}};
/*! js-yaml 4.1.0 https://github.com/nodeca/js-yaml @license MIT */
function Pe(e){return null==e}Re.styles=s`
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
  `,e([he({attribute:!1})],Re.prototype,"warnings",void 0),e([he({attribute:!1})],Re.prototype,"displayedRuleIds",void 0),e([he()],Re.prototype,"language",void 0),Re=e([ce("shabbat-warnings")],Re);var ze={isNothing:Pe,isObject:function(e){return"object"==typeof e&&null!==e},toArray:function(e){return Array.isArray(e)?e:Pe(e)?[]:[e]},repeat:function(e,t){var i,n="";for(i=0;i<t;i+=1)n+=e;return n},isNegativeZero:function(e){return 0===e&&Number.NEGATIVE_INFINITY===1/e},extend:function(e,t){var i,n,o,r;if(t)for(i=0,n=(r=Object.keys(t)).length;i<n;i+=1)e[o=r[i]]=t[o];return e}};function De(e,t){var i="",n=e.reason||"(unknown reason)";return e.mark?(e.mark.name&&(i+='in "'+e.mark.name+'" '),i+="("+(e.mark.line+1)+":"+(e.mark.column+1)+")",!t&&e.mark.snippet&&(i+="\n\n"+e.mark.snippet),n+" "+i):n}function We(e,t){Error.call(this),this.name="YAMLException",this.reason=e,this.mark=t,this.message=De(this,!1),Error.captureStackTrace?Error.captureStackTrace(this,this.constructor):this.stack=(new Error).stack||""}We.prototype=Object.create(Error.prototype),We.prototype.constructor=We,We.prototype.toString=function(e){return this.name+": "+De(this,e)};var Le=We;function Fe(e,t,i,n,o){var r="",s="",a=Math.floor(o/2)-1;return n-t>a&&(t=n-a+(r=" ... ").length),i-n>a&&(i=n+a-(s=" ...").length),{str:r+e.slice(t,i).replace(/\t/g,"→")+s,pos:n-t+r.length}}function Ue(e,t){return ze.repeat(" ",t-e.length)+e}var Be=function(e,t){if(t=Object.create(t||null),!e.buffer)return null;t.maxLength||(t.maxLength=79),"number"!=typeof t.indent&&(t.indent=1),"number"!=typeof t.linesBefore&&(t.linesBefore=3),"number"!=typeof t.linesAfter&&(t.linesAfter=2);for(var i,n=/\r?\n|\r|\0/g,o=[0],r=[],s=-1;i=n.exec(e.buffer);)r.push(i.index),o.push(i.index+i[0].length),e.position<=i.index&&s<0&&(s=o.length-2);s<0&&(s=o.length-1);var a,l,c="",d=Math.min(e.line+t.linesAfter,r.length).toString().length,u=t.maxLength-(t.indent+d+3);for(a=1;a<=t.linesBefore&&!(s-a<0);a++)l=Fe(e.buffer,o[s-a],r[s-a],e.position-(o[s]-o[s-a]),u),c=ze.repeat(" ",t.indent)+Ue((e.line-a+1).toString(),d)+" | "+l.str+"\n"+c;for(l=Fe(e.buffer,o[s],r[s],e.position,u),c+=ze.repeat(" ",t.indent)+Ue((e.line+1).toString(),d)+" | "+l.str+"\n",c+=ze.repeat("-",t.indent+d+3+l.pos)+"^\n",a=1;a<=t.linesAfter&&!(s+a>=r.length);a++)l=Fe(e.buffer,o[s+a],r[s+a],e.position-(o[s]-o[s+a]),u),c+=ze.repeat(" ",t.indent)+Ue((e.line+a+1).toString(),d)+" | "+l.str+"\n";return c.replace(/\n$/,"")},He=["kind","multi","resolve","construct","instanceOf","predicate","represent","representName","defaultStyle","styleAliases"],qe=["scalar","sequence","mapping"];var Ye=function(e,t){if(t=t||{},Object.keys(t).forEach(function(t){if(-1===He.indexOf(t))throw new Le('Unknown option "'+t+'" is met in definition of "'+e+'" YAML type.')}),this.options=t,this.tag=e,this.kind=t.kind||null,this.resolve=t.resolve||function(){return!0},this.construct=t.construct||function(e){return e},this.instanceOf=t.instanceOf||null,this.predicate=t.predicate||null,this.represent=t.represent||null,this.representName=t.representName||null,this.defaultStyle=t.defaultStyle||null,this.multi=t.multi||!1,this.styleAliases=function(e){var t={};return null!==e&&Object.keys(e).forEach(function(i){e[i].forEach(function(e){t[String(e)]=i})}),t}(t.styleAliases||null),-1===qe.indexOf(this.kind))throw new Le('Unknown kind "'+this.kind+'" is specified for "'+e+'" YAML type.')};function Ke(e,t){var i=[];return e[t].forEach(function(e){var t=i.length;i.forEach(function(i,n){i.tag===e.tag&&i.kind===e.kind&&i.multi===e.multi&&(t=n)}),i[t]=e}),i}function Ve(e){return this.extend(e)}Ve.prototype.extend=function(e){var t=[],i=[];if(e instanceof Ye)i.push(e);else if(Array.isArray(e))i=i.concat(e);else{if(!e||!Array.isArray(e.implicit)&&!Array.isArray(e.explicit))throw new Le("Schema.extend argument should be a Type, [ Type ], or a schema definition ({ implicit: [...], explicit: [...] })");e.implicit&&(t=t.concat(e.implicit)),e.explicit&&(i=i.concat(e.explicit))}t.forEach(function(e){if(!(e instanceof Ye))throw new Le("Specified list of YAML types (or a single Type object) contains a non-Type object.");if(e.loadKind&&"scalar"!==e.loadKind)throw new Le("There is a non-scalar type in the implicit list of a schema. Implicit resolving of such types is not supported.");if(e.multi)throw new Le("There is a multi type in the implicit list of a schema. Multi tags can only be listed as explicit.")}),i.forEach(function(e){if(!(e instanceof Ye))throw new Le("Specified list of YAML types (or a single Type object) contains a non-Type object.")});var n=Object.create(Ve.prototype);return n.implicit=(this.implicit||[]).concat(t),n.explicit=(this.explicit||[]).concat(i),n.compiledImplicit=Ke(n,"implicit"),n.compiledExplicit=Ke(n,"explicit"),n.compiledTypeMap=function(){var e,t,i={scalar:{},sequence:{},mapping:{},fallback:{},multi:{scalar:[],sequence:[],mapping:[],fallback:[]}};function n(e){e.multi?(i.multi[e.kind].push(e),i.multi.fallback.push(e)):i[e.kind][e.tag]=i.fallback[e.tag]=e}for(e=0,t=arguments.length;e<t;e+=1)arguments[e].forEach(n);return i}(n.compiledImplicit,n.compiledExplicit),n};var Ge=new Ve({explicit:[new Ye("tag:yaml.org,2002:str",{kind:"scalar",construct:function(e){return null!==e?e:""}}),new Ye("tag:yaml.org,2002:seq",{kind:"sequence",construct:function(e){return null!==e?e:[]}}),new Ye("tag:yaml.org,2002:map",{kind:"mapping",construct:function(e){return null!==e?e:{}}})]});var Je=new Ye("tag:yaml.org,2002:null",{kind:"scalar",resolve:function(e){if(null===e)return!0;var t=e.length;return 1===t&&"~"===e||4===t&&("null"===e||"Null"===e||"NULL"===e)},construct:function(){return null},predicate:function(e){return null===e},represent:{canonical:function(){return"~"},lowercase:function(){return"null"},uppercase:function(){return"NULL"},camelcase:function(){return"Null"},empty:function(){return""}},defaultStyle:"lowercase"});var Ze=new Ye("tag:yaml.org,2002:bool",{kind:"scalar",resolve:function(e){if(null===e)return!1;var t=e.length;return 4===t&&("true"===e||"True"===e||"TRUE"===e)||5===t&&("false"===e||"False"===e||"FALSE"===e)},construct:function(e){return"true"===e||"True"===e||"TRUE"===e},predicate:function(e){return"[object Boolean]"===Object.prototype.toString.call(e)},represent:{lowercase:function(e){return e?"true":"false"},uppercase:function(e){return e?"TRUE":"FALSE"},camelcase:function(e){return e?"True":"False"}},defaultStyle:"lowercase"});function Qe(e){return 48<=e&&e<=57||65<=e&&e<=70||97<=e&&e<=102}function Xe(e){return 48<=e&&e<=55}function et(e){return 48<=e&&e<=57}var tt=new Ye("tag:yaml.org,2002:int",{kind:"scalar",resolve:function(e){if(null===e)return!1;var t,i=e.length,n=0,o=!1;if(!i)return!1;if("-"!==(t=e[n])&&"+"!==t||(t=e[++n]),"0"===t){if(n+1===i)return!0;if("b"===(t=e[++n])){for(n++;n<i;n++)if("_"!==(t=e[n])){if("0"!==t&&"1"!==t)return!1;o=!0}return o&&"_"!==t}if("x"===t){for(n++;n<i;n++)if("_"!==(t=e[n])){if(!Qe(e.charCodeAt(n)))return!1;o=!0}return o&&"_"!==t}if("o"===t){for(n++;n<i;n++)if("_"!==(t=e[n])){if(!Xe(e.charCodeAt(n)))return!1;o=!0}return o&&"_"!==t}}if("_"===t)return!1;for(;n<i;n++)if("_"!==(t=e[n])){if(!et(e.charCodeAt(n)))return!1;o=!0}return!(!o||"_"===t)},construct:function(e){var t,i=e,n=1;if(-1!==i.indexOf("_")&&(i=i.replace(/_/g,"")),"-"!==(t=i[0])&&"+"!==t||("-"===t&&(n=-1),t=(i=i.slice(1))[0]),"0"===i)return 0;if("0"===t){if("b"===i[1])return n*parseInt(i.slice(2),2);if("x"===i[1])return n*parseInt(i.slice(2),16);if("o"===i[1])return n*parseInt(i.slice(2),8)}return n*parseInt(i,10)},predicate:function(e){return"[object Number]"===Object.prototype.toString.call(e)&&e%1==0&&!ze.isNegativeZero(e)},represent:{binary:function(e){return e>=0?"0b"+e.toString(2):"-0b"+e.toString(2).slice(1)},octal:function(e){return e>=0?"0o"+e.toString(8):"-0o"+e.toString(8).slice(1)},decimal:function(e){return e.toString(10)},hexadecimal:function(e){return e>=0?"0x"+e.toString(16).toUpperCase():"-0x"+e.toString(16).toUpperCase().slice(1)}},defaultStyle:"decimal",styleAliases:{binary:[2,"bin"],octal:[8,"oct"],decimal:[10,"dec"],hexadecimal:[16,"hex"]}}),it=new RegExp("^(?:[-+]?(?:[0-9][0-9_]*)(?:\\.[0-9_]*)?(?:[eE][-+]?[0-9]+)?|\\.[0-9_]+(?:[eE][-+]?[0-9]+)?|[-+]?\\.(?:inf|Inf|INF)|\\.(?:nan|NaN|NAN))$");var nt=/^[-+]?[0-9]+e/;var ot=new Ye("tag:yaml.org,2002:float",{kind:"scalar",resolve:function(e){return null!==e&&!(!it.test(e)||"_"===e[e.length-1])},construct:function(e){var t,i;return i="-"===(t=e.replace(/_/g,"").toLowerCase())[0]?-1:1,"+-".indexOf(t[0])>=0&&(t=t.slice(1)),".inf"===t?1===i?Number.POSITIVE_INFINITY:Number.NEGATIVE_INFINITY:".nan"===t?NaN:i*parseFloat(t,10)},predicate:function(e){return"[object Number]"===Object.prototype.toString.call(e)&&(e%1!=0||ze.isNegativeZero(e))},represent:function(e,t){var i;if(isNaN(e))switch(t){case"lowercase":return".nan";case"uppercase":return".NAN";case"camelcase":return".NaN"}else if(Number.POSITIVE_INFINITY===e)switch(t){case"lowercase":return".inf";case"uppercase":return".INF";case"camelcase":return".Inf"}else if(Number.NEGATIVE_INFINITY===e)switch(t){case"lowercase":return"-.inf";case"uppercase":return"-.INF";case"camelcase":return"-.Inf"}else if(ze.isNegativeZero(e))return"-0.0";return i=e.toString(10),nt.test(i)?i.replace("e",".e"):i},defaultStyle:"lowercase"}),rt=Ge.extend({implicit:[Je,Ze,tt,ot]}),st=new RegExp("^([0-9][0-9][0-9][0-9])-([0-9][0-9])-([0-9][0-9])$"),at=new RegExp("^([0-9][0-9][0-9][0-9])-([0-9][0-9]?)-([0-9][0-9]?)(?:[Tt]|[ \\t]+)([0-9][0-9]?):([0-9][0-9]):([0-9][0-9])(?:\\.([0-9]*))?(?:[ \\t]*(Z|([-+])([0-9][0-9]?)(?::([0-9][0-9]))?))?$");var lt=new Ye("tag:yaml.org,2002:timestamp",{kind:"scalar",resolve:function(e){return null!==e&&(null!==st.exec(e)||null!==at.exec(e))},construct:function(e){var t,i,n,o,r,s,a,l,c=0,d=null;if(null===(t=st.exec(e))&&(t=at.exec(e)),null===t)throw new Error("Date resolve error");if(i=+t[1],n=+t[2]-1,o=+t[3],!t[4])return new Date(Date.UTC(i,n,o));if(r=+t[4],s=+t[5],a=+t[6],t[7]){for(c=t[7].slice(0,3);c.length<3;)c+="0";c=+c}return t[9]&&(d=6e4*(60*+t[10]+ +(t[11]||0)),"-"===t[9]&&(d=-d)),l=new Date(Date.UTC(i,n,o,r,s,a,c)),d&&l.setTime(l.getTime()-d),l},instanceOf:Date,represent:function(e){return e.toISOString()}});var ct=new Ye("tag:yaml.org,2002:merge",{kind:"scalar",resolve:function(e){return"<<"===e||null===e}}),dt="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r";var ut=new Ye("tag:yaml.org,2002:binary",{kind:"scalar",resolve:function(e){if(null===e)return!1;var t,i,n=0,o=e.length,r=dt;for(i=0;i<o;i++)if(!((t=r.indexOf(e.charAt(i)))>64)){if(t<0)return!1;n+=6}return n%8==0},construct:function(e){var t,i,n=e.replace(/[\r\n=]/g,""),o=n.length,r=dt,s=0,a=[];for(t=0;t<o;t++)t%4==0&&t&&(a.push(s>>16&255),a.push(s>>8&255),a.push(255&s)),s=s<<6|r.indexOf(n.charAt(t));return 0===(i=o%4*6)?(a.push(s>>16&255),a.push(s>>8&255),a.push(255&s)):18===i?(a.push(s>>10&255),a.push(s>>2&255)):12===i&&a.push(s>>4&255),new Uint8Array(a)},predicate:function(e){return"[object Uint8Array]"===Object.prototype.toString.call(e)},represent:function(e){var t,i,n="",o=0,r=e.length,s=dt;for(t=0;t<r;t++)t%3==0&&t&&(n+=s[o>>18&63],n+=s[o>>12&63],n+=s[o>>6&63],n+=s[63&o]),o=(o<<8)+e[t];return 0===(i=r%3)?(n+=s[o>>18&63],n+=s[o>>12&63],n+=s[o>>6&63],n+=s[63&o]):2===i?(n+=s[o>>10&63],n+=s[o>>4&63],n+=s[o<<2&63],n+=s[64]):1===i&&(n+=s[o>>2&63],n+=s[o<<4&63],n+=s[64],n+=s[64]),n}}),ht=Object.prototype.hasOwnProperty,pt=Object.prototype.toString;var gt=new Ye("tag:yaml.org,2002:omap",{kind:"sequence",resolve:function(e){if(null===e)return!0;var t,i,n,o,r,s=[],a=e;for(t=0,i=a.length;t<i;t+=1){if(n=a[t],r=!1,"[object Object]"!==pt.call(n))return!1;for(o in n)if(ht.call(n,o)){if(r)return!1;r=!0}if(!r)return!1;if(-1!==s.indexOf(o))return!1;s.push(o)}return!0},construct:function(e){return null!==e?e:[]}}),ft=Object.prototype.toString;var _t=new Ye("tag:yaml.org,2002:pairs",{kind:"sequence",resolve:function(e){if(null===e)return!0;var t,i,n,o,r,s=e;for(r=new Array(s.length),t=0,i=s.length;t<i;t+=1){if(n=s[t],"[object Object]"!==ft.call(n))return!1;if(1!==(o=Object.keys(n)).length)return!1;r[t]=[o[0],n[o[0]]]}return!0},construct:function(e){if(null===e)return[];var t,i,n,o,r,s=e;for(r=new Array(s.length),t=0,i=s.length;t<i;t+=1)n=s[t],o=Object.keys(n),r[t]=[o[0],n[o[0]]];return r}}),bt=Object.prototype.hasOwnProperty;var mt=new Ye("tag:yaml.org,2002:set",{kind:"mapping",resolve:function(e){if(null===e)return!0;var t,i=e;for(t in i)if(bt.call(i,t)&&null!==i[t])return!1;return!0},construct:function(e){return null!==e?e:{}}}),vt=rt.extend({implicit:[lt,ct],explicit:[ut,gt,_t,mt]}),yt=Object.prototype.hasOwnProperty,$t=/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x84\x86-\x9F\uFFFE\uFFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]/,wt=/[\x85\u2028\u2029]/,xt=/[,\[\]\{\}]/,kt=/^(?:!|!!|![a-z\-]+!)$/i,At=/^(?:!|[^,\[\]\{\}])(?:%[0-9a-f]{2}|[0-9a-z\-#;\/\?:@&=\+\$,_\.!~\*'\(\)\[\]])*$/i;function Ct(e){return Object.prototype.toString.call(e)}function St(e){return 10===e||13===e}function Et(e){return 9===e||32===e}function Ot(e){return 9===e||32===e||10===e||13===e}function Tt(e){return 44===e||91===e||93===e||123===e||125===e}function It(e){var t;return 48<=e&&e<=57?e-48:97<=(t=32|e)&&t<=102?t-97+10:-1}function Nt(e){return 120===e?2:117===e?4:85===e?8:0}function jt(e){return 48<=e&&e<=57?e-48:-1}function Mt(e){return 48===e?"\0":97===e?"":98===e?"\b":116===e||9===e?"\t":110===e?"\n":118===e?"\v":102===e?"\f":114===e?"\r":101===e?"":32===e?" ":34===e?'"':47===e?"/":92===e?"\\":78===e?"":95===e?" ":76===e?"\u2028":80===e?"\u2029":""}function Rt(e){return e<=65535?String.fromCharCode(e):String.fromCharCode(55296+(e-65536>>10),56320+(e-65536&1023))}for(var Pt=new Array(256),zt=new Array(256),Dt=0;Dt<256;Dt++)Pt[Dt]=Mt(Dt)?1:0,zt[Dt]=Mt(Dt);function Wt(e,t){this.input=e,this.filename=t.filename||null,this.schema=t.schema||vt,this.onWarning=t.onWarning||null,this.legacy=t.legacy||!1,this.json=t.json||!1,this.listener=t.listener||null,this.implicitTypes=this.schema.compiledImplicit,this.typeMap=this.schema.compiledTypeMap,this.length=e.length,this.position=0,this.line=0,this.lineStart=0,this.lineIndent=0,this.firstTabInLine=-1,this.documents=[]}function Lt(e,t){var i={name:e.filename,buffer:e.input.slice(0,-1),position:e.position,line:e.line,column:e.position-e.lineStart};return i.snippet=Be(i),new Le(t,i)}function Ft(e,t){throw Lt(e,t)}function Ut(e,t){e.onWarning&&e.onWarning.call(null,Lt(e,t))}var Bt={YAML:function(e,t,i){var n,o,r;null!==e.version&&Ft(e,"duplication of %YAML directive"),1!==i.length&&Ft(e,"YAML directive accepts exactly one argument"),null===(n=/^([0-9]+)\.([0-9]+)$/.exec(i[0]))&&Ft(e,"ill-formed argument of the YAML directive"),o=parseInt(n[1],10),r=parseInt(n[2],10),1!==o&&Ft(e,"unacceptable YAML version of the document"),e.version=i[0],e.checkLineBreaks=r<2,1!==r&&2!==r&&Ut(e,"unsupported YAML version of the document")},TAG:function(e,t,i){var n,o;2!==i.length&&Ft(e,"TAG directive accepts exactly two arguments"),n=i[0],o=i[1],kt.test(n)||Ft(e,"ill-formed tag handle (first argument) of the TAG directive"),yt.call(e.tagMap,n)&&Ft(e,'there is a previously declared suffix for "'+n+'" tag handle'),At.test(o)||Ft(e,"ill-formed tag prefix (second argument) of the TAG directive");try{o=decodeURIComponent(o)}catch(t){Ft(e,"tag prefix is malformed: "+o)}e.tagMap[n]=o}};function Ht(e,t,i,n){var o,r,s,a;if(t<i){if(a=e.input.slice(t,i),n)for(o=0,r=a.length;o<r;o+=1)9===(s=a.charCodeAt(o))||32<=s&&s<=1114111||Ft(e,"expected valid JSON character");else $t.test(a)&&Ft(e,"the stream contains non-printable characters");e.result+=a}}function qt(e,t,i,n){var o,r,s,a;for(ze.isObject(i)||Ft(e,"cannot merge mappings; the provided source object is unacceptable"),s=0,a=(o=Object.keys(i)).length;s<a;s+=1)r=o[s],yt.call(t,r)||(t[r]=i[r],n[r]=!0)}function Yt(e,t,i,n,o,r,s,a,l){var c,d;if(Array.isArray(o))for(c=0,d=(o=Array.prototype.slice.call(o)).length;c<d;c+=1)Array.isArray(o[c])&&Ft(e,"nested arrays are not supported inside keys"),"object"==typeof o&&"[object Object]"===Ct(o[c])&&(o[c]="[object Object]");if("object"==typeof o&&"[object Object]"===Ct(o)&&(o="[object Object]"),o=String(o),null===t&&(t={}),"tag:yaml.org,2002:merge"===n)if(Array.isArray(r))for(c=0,d=r.length;c<d;c+=1)qt(e,t,r[c],i);else qt(e,t,r,i);else e.json||yt.call(i,o)||!yt.call(t,o)||(e.line=s||e.line,e.lineStart=a||e.lineStart,e.position=l||e.position,Ft(e,"duplicated mapping key")),"__proto__"===o?Object.defineProperty(t,o,{configurable:!0,enumerable:!0,writable:!0,value:r}):t[o]=r,delete i[o];return t}function Kt(e){var t;10===(t=e.input.charCodeAt(e.position))?e.position++:13===t?(e.position++,10===e.input.charCodeAt(e.position)&&e.position++):Ft(e,"a line break is expected"),e.line+=1,e.lineStart=e.position,e.firstTabInLine=-1}function Vt(e,t,i){for(var n=0,o=e.input.charCodeAt(e.position);0!==o;){for(;Et(o);)9===o&&-1===e.firstTabInLine&&(e.firstTabInLine=e.position),o=e.input.charCodeAt(++e.position);if(t&&35===o)do{o=e.input.charCodeAt(++e.position)}while(10!==o&&13!==o&&0!==o);if(!St(o))break;for(Kt(e),o=e.input.charCodeAt(e.position),n++,e.lineIndent=0;32===o;)e.lineIndent++,o=e.input.charCodeAt(++e.position)}return-1!==i&&0!==n&&e.lineIndent<i&&Ut(e,"deficient indentation"),n}function Gt(e){var t,i=e.position;return!(45!==(t=e.input.charCodeAt(i))&&46!==t||t!==e.input.charCodeAt(i+1)||t!==e.input.charCodeAt(i+2)||(i+=3,0!==(t=e.input.charCodeAt(i))&&!Ot(t)))}function Jt(e,t){1===t?e.result+=" ":t>1&&(e.result+=ze.repeat("\n",t-1))}function Zt(e,t){var i,n,o=e.tag,r=e.anchor,s=[],a=!1;if(-1!==e.firstTabInLine)return!1;for(null!==e.anchor&&(e.anchorMap[e.anchor]=s),n=e.input.charCodeAt(e.position);0!==n&&(-1!==e.firstTabInLine&&(e.position=e.firstTabInLine,Ft(e,"tab characters must not be used in indentation")),45===n)&&Ot(e.input.charCodeAt(e.position+1));)if(a=!0,e.position++,Vt(e,!0,-1)&&e.lineIndent<=t)s.push(null),n=e.input.charCodeAt(e.position);else if(i=e.line,ei(e,t,3,!1,!0),s.push(e.result),Vt(e,!0,-1),n=e.input.charCodeAt(e.position),(e.line===i||e.lineIndent>t)&&0!==n)Ft(e,"bad indentation of a sequence entry");else if(e.lineIndent<t)break;return!!a&&(e.tag=o,e.anchor=r,e.kind="sequence",e.result=s,!0)}function Qt(e){var t,i,n,o,r=!1,s=!1;if(33!==(o=e.input.charCodeAt(e.position)))return!1;if(null!==e.tag&&Ft(e,"duplication of a tag property"),60===(o=e.input.charCodeAt(++e.position))?(r=!0,o=e.input.charCodeAt(++e.position)):33===o?(s=!0,i="!!",o=e.input.charCodeAt(++e.position)):i="!",t=e.position,r){do{o=e.input.charCodeAt(++e.position)}while(0!==o&&62!==o);e.position<e.length?(n=e.input.slice(t,e.position),o=e.input.charCodeAt(++e.position)):Ft(e,"unexpected end of the stream within a verbatim tag")}else{for(;0!==o&&!Ot(o);)33===o&&(s?Ft(e,"tag suffix cannot contain exclamation marks"):(i=e.input.slice(t-1,e.position+1),kt.test(i)||Ft(e,"named tag handle cannot contain such characters"),s=!0,t=e.position+1)),o=e.input.charCodeAt(++e.position);n=e.input.slice(t,e.position),xt.test(n)&&Ft(e,"tag suffix cannot contain flow indicator characters")}n&&!At.test(n)&&Ft(e,"tag name cannot contain such characters: "+n);try{n=decodeURIComponent(n)}catch(t){Ft(e,"tag name is malformed: "+n)}return r?e.tag=n:yt.call(e.tagMap,i)?e.tag=e.tagMap[i]+n:"!"===i?e.tag="!"+n:"!!"===i?e.tag="tag:yaml.org,2002:"+n:Ft(e,'undeclared tag handle "'+i+'"'),!0}function Xt(e){var t,i;if(38!==(i=e.input.charCodeAt(e.position)))return!1;for(null!==e.anchor&&Ft(e,"duplication of an anchor property"),i=e.input.charCodeAt(++e.position),t=e.position;0!==i&&!Ot(i)&&!Tt(i);)i=e.input.charCodeAt(++e.position);return e.position===t&&Ft(e,"name of an anchor node must contain at least one character"),e.anchor=e.input.slice(t,e.position),!0}function ei(e,t,i,n,o){var r,s,a,l,c,d,u,h,p,g=1,f=!1,_=!1;if(null!==e.listener&&e.listener("open",e),e.tag=null,e.anchor=null,e.kind=null,e.result=null,r=s=a=4===i||3===i,n&&Vt(e,!0,-1)&&(f=!0,e.lineIndent>t?g=1:e.lineIndent===t?g=0:e.lineIndent<t&&(g=-1)),1===g)for(;Qt(e)||Xt(e);)Vt(e,!0,-1)?(f=!0,a=r,e.lineIndent>t?g=1:e.lineIndent===t?g=0:e.lineIndent<t&&(g=-1)):a=!1;if(a&&(a=f||o),1!==g&&4!==i||(h=1===i||2===i?t:t+1,p=e.position-e.lineStart,1===g?a&&(Zt(e,p)||function(e,t,i){var n,o,r,s,a,l,c,d=e.tag,u=e.anchor,h={},p=Object.create(null),g=null,f=null,_=null,b=!1,m=!1;if(-1!==e.firstTabInLine)return!1;for(null!==e.anchor&&(e.anchorMap[e.anchor]=h),c=e.input.charCodeAt(e.position);0!==c;){if(b||-1===e.firstTabInLine||(e.position=e.firstTabInLine,Ft(e,"tab characters must not be used in indentation")),n=e.input.charCodeAt(e.position+1),r=e.line,63!==c&&58!==c||!Ot(n)){if(s=e.line,a=e.lineStart,l=e.position,!ei(e,i,2,!1,!0))break;if(e.line===r){for(c=e.input.charCodeAt(e.position);Et(c);)c=e.input.charCodeAt(++e.position);if(58===c)Ot(c=e.input.charCodeAt(++e.position))||Ft(e,"a whitespace character is expected after the key-value separator within a block mapping"),b&&(Yt(e,h,p,g,f,null,s,a,l),g=f=_=null),m=!0,b=!1,o=!1,g=e.tag,f=e.result;else{if(!m)return e.tag=d,e.anchor=u,!0;Ft(e,"can not read an implicit mapping pair; a colon is missed")}}else{if(!m)return e.tag=d,e.anchor=u,!0;Ft(e,"can not read a block mapping entry; a multiline key may not be an implicit key")}}else 63===c?(b&&(Yt(e,h,p,g,f,null,s,a,l),g=f=_=null),m=!0,b=!0,o=!0):b?(b=!1,o=!0):Ft(e,"incomplete explicit mapping pair; a key node is missed; or followed by a non-tabulated empty line"),e.position+=1,c=n;if((e.line===r||e.lineIndent>t)&&(b&&(s=e.line,a=e.lineStart,l=e.position),ei(e,t,4,!0,o)&&(b?f=e.result:_=e.result),b||(Yt(e,h,p,g,f,_,s,a,l),g=f=_=null),Vt(e,!0,-1),c=e.input.charCodeAt(e.position)),(e.line===r||e.lineIndent>t)&&0!==c)Ft(e,"bad indentation of a mapping entry");else if(e.lineIndent<t)break}return b&&Yt(e,h,p,g,f,null,s,a,l),m&&(e.tag=d,e.anchor=u,e.kind="mapping",e.result=h),m}(e,p,h))||function(e,t){var i,n,o,r,s,a,l,c,d,u,h,p,g=!0,f=e.tag,_=e.anchor,b=Object.create(null);if(91===(p=e.input.charCodeAt(e.position)))s=93,c=!1,r=[];else{if(123!==p)return!1;s=125,c=!0,r={}}for(null!==e.anchor&&(e.anchorMap[e.anchor]=r),p=e.input.charCodeAt(++e.position);0!==p;){if(Vt(e,!0,t),(p=e.input.charCodeAt(e.position))===s)return e.position++,e.tag=f,e.anchor=_,e.kind=c?"mapping":"sequence",e.result=r,!0;g?44===p&&Ft(e,"expected the node content, but found ','"):Ft(e,"missed comma between flow collection entries"),h=null,a=l=!1,63===p&&Ot(e.input.charCodeAt(e.position+1))&&(a=l=!0,e.position++,Vt(e,!0,t)),i=e.line,n=e.lineStart,o=e.position,ei(e,t,1,!1,!0),u=e.tag,d=e.result,Vt(e,!0,t),p=e.input.charCodeAt(e.position),!l&&e.line!==i||58!==p||(a=!0,p=e.input.charCodeAt(++e.position),Vt(e,!0,t),ei(e,t,1,!1,!0),h=e.result),c?Yt(e,r,b,u,d,h,i,n,o):a?r.push(Yt(e,null,b,u,d,h,i,n,o)):r.push(d),Vt(e,!0,t),44===(p=e.input.charCodeAt(e.position))?(g=!0,p=e.input.charCodeAt(++e.position)):g=!1}Ft(e,"unexpected end of the stream within a flow collection")}(e,h)?_=!0:(s&&function(e,t){var i,n,o,r,s=1,a=!1,l=!1,c=t,d=0,u=!1;if(124===(r=e.input.charCodeAt(e.position)))n=!1;else{if(62!==r)return!1;n=!0}for(e.kind="scalar",e.result="";0!==r;)if(43===(r=e.input.charCodeAt(++e.position))||45===r)1===s?s=43===r?3:2:Ft(e,"repeat of a chomping mode identifier");else{if(!((o=jt(r))>=0))break;0===o?Ft(e,"bad explicit indentation width of a block scalar; it cannot be less than one"):l?Ft(e,"repeat of an indentation width identifier"):(c=t+o-1,l=!0)}if(Et(r)){do{r=e.input.charCodeAt(++e.position)}while(Et(r));if(35===r)do{r=e.input.charCodeAt(++e.position)}while(!St(r)&&0!==r)}for(;0!==r;){for(Kt(e),e.lineIndent=0,r=e.input.charCodeAt(e.position);(!l||e.lineIndent<c)&&32===r;)e.lineIndent++,r=e.input.charCodeAt(++e.position);if(!l&&e.lineIndent>c&&(c=e.lineIndent),St(r))d++;else{if(e.lineIndent<c){3===s?e.result+=ze.repeat("\n",a?1+d:d):1===s&&a&&(e.result+="\n");break}for(n?Et(r)?(u=!0,e.result+=ze.repeat("\n",a?1+d:d)):u?(u=!1,e.result+=ze.repeat("\n",d+1)):0===d?a&&(e.result+=" "):e.result+=ze.repeat("\n",d):e.result+=ze.repeat("\n",a?1+d:d),a=!0,l=!0,d=0,i=e.position;!St(r)&&0!==r;)r=e.input.charCodeAt(++e.position);Ht(e,i,e.position,!1)}}return!0}(e,h)||function(e,t){var i,n,o;if(39!==(i=e.input.charCodeAt(e.position)))return!1;for(e.kind="scalar",e.result="",e.position++,n=o=e.position;0!==(i=e.input.charCodeAt(e.position));)if(39===i){if(Ht(e,n,e.position,!0),39!==(i=e.input.charCodeAt(++e.position)))return!0;n=e.position,e.position++,o=e.position}else St(i)?(Ht(e,n,o,!0),Jt(e,Vt(e,!1,t)),n=o=e.position):e.position===e.lineStart&&Gt(e)?Ft(e,"unexpected end of the document within a single quoted scalar"):(e.position++,o=e.position);Ft(e,"unexpected end of the stream within a single quoted scalar")}(e,h)||function(e,t){var i,n,o,r,s,a;if(34!==(a=e.input.charCodeAt(e.position)))return!1;for(e.kind="scalar",e.result="",e.position++,i=n=e.position;0!==(a=e.input.charCodeAt(e.position));){if(34===a)return Ht(e,i,e.position,!0),e.position++,!0;if(92===a){if(Ht(e,i,e.position,!0),St(a=e.input.charCodeAt(++e.position)))Vt(e,!1,t);else if(a<256&&Pt[a])e.result+=zt[a],e.position++;else if((s=Nt(a))>0){for(o=s,r=0;o>0;o--)(s=It(a=e.input.charCodeAt(++e.position)))>=0?r=(r<<4)+s:Ft(e,"expected hexadecimal character");e.result+=Rt(r),e.position++}else Ft(e,"unknown escape sequence");i=n=e.position}else St(a)?(Ht(e,i,n,!0),Jt(e,Vt(e,!1,t)),i=n=e.position):e.position===e.lineStart&&Gt(e)?Ft(e,"unexpected end of the document within a double quoted scalar"):(e.position++,n=e.position)}Ft(e,"unexpected end of the stream within a double quoted scalar")}(e,h)?_=!0:!function(e){var t,i,n;if(42!==(n=e.input.charCodeAt(e.position)))return!1;for(n=e.input.charCodeAt(++e.position),t=e.position;0!==n&&!Ot(n)&&!Tt(n);)n=e.input.charCodeAt(++e.position);return e.position===t&&Ft(e,"name of an alias node must contain at least one character"),i=e.input.slice(t,e.position),yt.call(e.anchorMap,i)||Ft(e,'unidentified alias "'+i+'"'),e.result=e.anchorMap[i],Vt(e,!0,-1),!0}(e)?function(e,t,i){var n,o,r,s,a,l,c,d,u=e.kind,h=e.result;if(Ot(d=e.input.charCodeAt(e.position))||Tt(d)||35===d||38===d||42===d||33===d||124===d||62===d||39===d||34===d||37===d||64===d||96===d)return!1;if((63===d||45===d)&&(Ot(n=e.input.charCodeAt(e.position+1))||i&&Tt(n)))return!1;for(e.kind="scalar",e.result="",o=r=e.position,s=!1;0!==d;){if(58===d){if(Ot(n=e.input.charCodeAt(e.position+1))||i&&Tt(n))break}else if(35===d){if(Ot(e.input.charCodeAt(e.position-1)))break}else{if(e.position===e.lineStart&&Gt(e)||i&&Tt(d))break;if(St(d)){if(a=e.line,l=e.lineStart,c=e.lineIndent,Vt(e,!1,-1),e.lineIndent>=t){s=!0,d=e.input.charCodeAt(e.position);continue}e.position=r,e.line=a,e.lineStart=l,e.lineIndent=c;break}}s&&(Ht(e,o,r,!1),Jt(e,e.line-a),o=r=e.position,s=!1),Et(d)||(r=e.position+1),d=e.input.charCodeAt(++e.position)}return Ht(e,o,r,!1),!!e.result||(e.kind=u,e.result=h,!1)}(e,h,1===i)&&(_=!0,null===e.tag&&(e.tag="?")):(_=!0,null===e.tag&&null===e.anchor||Ft(e,"alias node should not have any properties")),null!==e.anchor&&(e.anchorMap[e.anchor]=e.result)):0===g&&(_=a&&Zt(e,p))),null===e.tag)null!==e.anchor&&(e.anchorMap[e.anchor]=e.result);else if("?"===e.tag){for(null!==e.result&&"scalar"!==e.kind&&Ft(e,'unacceptable node kind for !<?> tag; it should be "scalar", not "'+e.kind+'"'),l=0,c=e.implicitTypes.length;l<c;l+=1)if((u=e.implicitTypes[l]).resolve(e.result)){e.result=u.construct(e.result),e.tag=u.tag,null!==e.anchor&&(e.anchorMap[e.anchor]=e.result);break}}else if("!"!==e.tag){if(yt.call(e.typeMap[e.kind||"fallback"],e.tag))u=e.typeMap[e.kind||"fallback"][e.tag];else for(u=null,l=0,c=(d=e.typeMap.multi[e.kind||"fallback"]).length;l<c;l+=1)if(e.tag.slice(0,d[l].tag.length)===d[l].tag){u=d[l];break}u||Ft(e,"unknown tag !<"+e.tag+">"),null!==e.result&&u.kind!==e.kind&&Ft(e,"unacceptable node kind for !<"+e.tag+'> tag; it should be "'+u.kind+'", not "'+e.kind+'"'),u.resolve(e.result,e.tag)?(e.result=u.construct(e.result,e.tag),null!==e.anchor&&(e.anchorMap[e.anchor]=e.result)):Ft(e,"cannot resolve a node with !<"+e.tag+"> explicit tag")}return null!==e.listener&&e.listener("close",e),null!==e.tag||null!==e.anchor||_}function ti(e){var t,i,n,o,r=e.position,s=!1;for(e.version=null,e.checkLineBreaks=e.legacy,e.tagMap=Object.create(null),e.anchorMap=Object.create(null);0!==(o=e.input.charCodeAt(e.position))&&(Vt(e,!0,-1),o=e.input.charCodeAt(e.position),!(e.lineIndent>0||37!==o));){for(s=!0,o=e.input.charCodeAt(++e.position),t=e.position;0!==o&&!Ot(o);)o=e.input.charCodeAt(++e.position);for(n=[],(i=e.input.slice(t,e.position)).length<1&&Ft(e,"directive name must not be less than one character in length");0!==o;){for(;Et(o);)o=e.input.charCodeAt(++e.position);if(35===o){do{o=e.input.charCodeAt(++e.position)}while(0!==o&&!St(o));break}if(St(o))break;for(t=e.position;0!==o&&!Ot(o);)o=e.input.charCodeAt(++e.position);n.push(e.input.slice(t,e.position))}0!==o&&Kt(e),yt.call(Bt,i)?Bt[i](e,i,n):Ut(e,'unknown document directive "'+i+'"')}Vt(e,!0,-1),0===e.lineIndent&&45===e.input.charCodeAt(e.position)&&45===e.input.charCodeAt(e.position+1)&&45===e.input.charCodeAt(e.position+2)?(e.position+=3,Vt(e,!0,-1)):s&&Ft(e,"directives end mark is expected"),ei(e,e.lineIndent-1,4,!1,!0),Vt(e,!0,-1),e.checkLineBreaks&&wt.test(e.input.slice(r,e.position))&&Ut(e,"non-ASCII line breaks are interpreted as content"),e.documents.push(e.result),e.position===e.lineStart&&Gt(e)?46===e.input.charCodeAt(e.position)&&(e.position+=3,Vt(e,!0,-1)):e.position<e.length-1&&Ft(e,"end of the stream or a document separator is expected")}var ii={load:function(e,t){var i=function(e,t){t=t||{},0!==(e=String(e)).length&&(10!==e.charCodeAt(e.length-1)&&13!==e.charCodeAt(e.length-1)&&(e+="\n"),65279===e.charCodeAt(0)&&(e=e.slice(1)));var i=new Wt(e,t),n=e.indexOf("\0");for(-1!==n&&(i.position=n,Ft(i,"null byte is not allowed in input")),i.input+="\0";32===i.input.charCodeAt(i.position);)i.lineIndent+=1,i.position+=1;for(;i.position<i.length-1;)ti(i);return i.documents}(e,t);if(0!==i.length){if(1===i.length)return i[0];throw new Le("expected a single document in the stream, but found more")}}},ni=Object.prototype.toString,oi=Object.prototype.hasOwnProperty,ri=65279,si={0:"\\0",7:"\\a",8:"\\b",9:"\\t",10:"\\n",11:"\\v",12:"\\f",13:"\\r",27:"\\e",34:'\\"',92:"\\\\",133:"\\N",160:"\\_",8232:"\\L",8233:"\\P"},ai=["y","Y","yes","Yes","YES","on","On","ON","n","N","no","No","NO","off","Off","OFF"],li=/^[-+]?[0-9_]+(?::[0-9_]+)+(?:\.[0-9_]*)?$/;function ci(e){var t,i,n;if(t=e.toString(16).toUpperCase(),e<=255)i="x",n=2;else if(e<=65535)i="u",n=4;else{if(!(e<=4294967295))throw new Le("code point within a string may not be greater than 0xFFFFFFFF");i="U",n=8}return"\\"+i+ze.repeat("0",n-t.length)+t}function di(e){this.schema=e.schema||vt,this.indent=Math.max(1,e.indent||2),this.noArrayIndent=e.noArrayIndent||!1,this.skipInvalid=e.skipInvalid||!1,this.flowLevel=ze.isNothing(e.flowLevel)?-1:e.flowLevel,this.styleMap=function(e,t){var i,n,o,r,s,a,l;if(null===t)return{};for(i={},o=0,r=(n=Object.keys(t)).length;o<r;o+=1)s=n[o],a=String(t[s]),"!!"===s.slice(0,2)&&(s="tag:yaml.org,2002:"+s.slice(2)),(l=e.compiledTypeMap.fallback[s])&&oi.call(l.styleAliases,a)&&(a=l.styleAliases[a]),i[s]=a;return i}(this.schema,e.styles||null),this.sortKeys=e.sortKeys||!1,this.lineWidth=e.lineWidth||80,this.noRefs=e.noRefs||!1,this.noCompatMode=e.noCompatMode||!1,this.condenseFlow=e.condenseFlow||!1,this.quotingType='"'===e.quotingType?2:1,this.forceQuotes=e.forceQuotes||!1,this.replacer="function"==typeof e.replacer?e.replacer:null,this.implicitTypes=this.schema.compiledImplicit,this.explicitTypes=this.schema.compiledExplicit,this.tag=null,this.result="",this.duplicates=[],this.usedDuplicates=null}function ui(e,t){for(var i,n=ze.repeat(" ",t),o=0,r=-1,s="",a=e.length;o<a;)-1===(r=e.indexOf("\n",o))?(i=e.slice(o),o=a):(i=e.slice(o,r+1),o=r+1),i.length&&"\n"!==i&&(s+=n),s+=i;return s}function hi(e,t){return"\n"+ze.repeat(" ",e.indent*t)}function pi(e){return 32===e||9===e}function gi(e){return 32<=e&&e<=126||161<=e&&e<=55295&&8232!==e&&8233!==e||57344<=e&&e<=65533&&e!==ri||65536<=e&&e<=1114111}function fi(e){return gi(e)&&e!==ri&&13!==e&&10!==e}function _i(e,t,i){var n=fi(e),o=n&&!pi(e);return(i?n:n&&44!==e&&91!==e&&93!==e&&123!==e&&125!==e)&&35!==e&&!(58===t&&!o)||fi(t)&&!pi(t)&&35===e||58===t&&o}function bi(e,t){var i,n=e.charCodeAt(t);return n>=55296&&n<=56319&&t+1<e.length&&(i=e.charCodeAt(t+1))>=56320&&i<=57343?1024*(n-55296)+i-56320+65536:n}function mi(e){return/^\n* /.test(e)}function vi(e,t,i,n,o,r,s,a){var l,c=0,d=null,u=!1,h=!1,p=-1!==n,g=-1,f=function(e){return gi(e)&&e!==ri&&!pi(e)&&45!==e&&63!==e&&58!==e&&44!==e&&91!==e&&93!==e&&123!==e&&125!==e&&35!==e&&38!==e&&42!==e&&33!==e&&124!==e&&61!==e&&62!==e&&39!==e&&34!==e&&37!==e&&64!==e&&96!==e}(bi(e,0))&&function(e){return!pi(e)&&58!==e}(bi(e,e.length-1));if(t||s)for(l=0;l<e.length;c>=65536?l+=2:l++){if(!gi(c=bi(e,l)))return 5;f=f&&_i(c,d,a),d=c}else{for(l=0;l<e.length;c>=65536?l+=2:l++){if(10===(c=bi(e,l)))u=!0,p&&(h=h||l-g-1>n&&" "!==e[g+1],g=l);else if(!gi(c))return 5;f=f&&_i(c,d,a),d=c}h=h||p&&l-g-1>n&&" "!==e[g+1]}return u||h?i>9&&mi(e)?5:s?2===r?5:2:h?4:3:!f||s||o(e)?2===r?5:2:1}function yi(e,t,i,n,o){e.dump=function(){if(0===t.length)return 2===e.quotingType?'""':"''";if(!e.noCompatMode&&(-1!==ai.indexOf(t)||li.test(t)))return 2===e.quotingType?'"'+t+'"':"'"+t+"'";var r=e.indent*Math.max(1,i),s=-1===e.lineWidth?-1:Math.max(Math.min(e.lineWidth,40),e.lineWidth-r),a=n||e.flowLevel>-1&&i>=e.flowLevel;switch(vi(t,a,e.indent,s,function(t){return function(e,t){var i,n;for(i=0,n=e.implicitTypes.length;i<n;i+=1)if(e.implicitTypes[i].resolve(t))return!0;return!1}(e,t)},e.quotingType,e.forceQuotes&&!n,o)){case 1:return t;case 2:return"'"+t.replace(/'/g,"''")+"'";case 3:return"|"+$i(t,e.indent)+wi(ui(t,r));case 4:return">"+$i(t,e.indent)+wi(ui(function(e,t){var i,n,o=/(\n+)([^\n]*)/g,r=(a=e.indexOf("\n"),a=-1!==a?a:e.length,o.lastIndex=a,xi(e.slice(0,a),t)),s="\n"===e[0]||" "===e[0];var a;for(;n=o.exec(e);){var l=n[1],c=n[2];i=" "===c[0],r+=l+(s||i||""===c?"":"\n")+xi(c,t),s=i}return r}(t,s),r));case 5:return'"'+function(e){for(var t,i="",n=0,o=0;o<e.length;n>=65536?o+=2:o++)n=bi(e,o),!(t=si[n])&&gi(n)?(i+=e[o],n>=65536&&(i+=e[o+1])):i+=t||ci(n);return i}(t)+'"';default:throw new Le("impossible error: invalid scalar style")}}()}function $i(e,t){var i=mi(e)?String(t):"",n="\n"===e[e.length-1];return i+(n&&("\n"===e[e.length-2]||"\n"===e)?"+":n?"":"-")+"\n"}function wi(e){return"\n"===e[e.length-1]?e.slice(0,-1):e}function xi(e,t){if(""===e||" "===e[0])return e;for(var i,n,o=/ [^ ]/g,r=0,s=0,a=0,l="";i=o.exec(e);)(a=i.index)-r>t&&(n=s>r?s:a,l+="\n"+e.slice(r,n),r=n+1),s=a;return l+="\n",e.length-r>t&&s>r?l+=e.slice(r,s)+"\n"+e.slice(s+1):l+=e.slice(r),l.slice(1)}function ki(e,t,i,n){var o,r,s,a="",l=e.tag;for(o=0,r=i.length;o<r;o+=1)s=i[o],e.replacer&&(s=e.replacer.call(i,String(o),s)),(Ci(e,t+1,s,!0,!0,!1,!0)||void 0===s&&Ci(e,t+1,null,!0,!0,!1,!0))&&(n&&""===a||(a+=hi(e,t)),e.dump&&10===e.dump.charCodeAt(0)?a+="-":a+="- ",a+=e.dump);e.tag=l,e.dump=a||"[]"}function Ai(e,t,i){var n,o,r,s,a,l;for(r=0,s=(o=i?e.explicitTypes:e.implicitTypes).length;r<s;r+=1)if(((a=o[r]).instanceOf||a.predicate)&&(!a.instanceOf||"object"==typeof t&&t instanceof a.instanceOf)&&(!a.predicate||a.predicate(t))){if(i?a.multi&&a.representName?e.tag=a.representName(t):e.tag=a.tag:e.tag="?",a.represent){if(l=e.styleMap[a.tag]||a.defaultStyle,"[object Function]"===ni.call(a.represent))n=a.represent(t,l);else{if(!oi.call(a.represent,l))throw new Le("!<"+a.tag+'> tag resolver accepts not "'+l+'" style');n=a.represent[l](t,l)}e.dump=n}return!0}return!1}function Ci(e,t,i,n,o,r,s){e.tag=null,e.dump=i,Ai(e,i,!1)||Ai(e,i,!0);var a,l=ni.call(e.dump),c=n;n&&(n=e.flowLevel<0||e.flowLevel>t);var d,u,h="[object Object]"===l||"[object Array]"===l;if(h&&(u=-1!==(d=e.duplicates.indexOf(i))),(null!==e.tag&&"?"!==e.tag||u||2!==e.indent&&t>0)&&(o=!1),u&&e.usedDuplicates[d])e.dump="*ref_"+d;else{if(h&&u&&!e.usedDuplicates[d]&&(e.usedDuplicates[d]=!0),"[object Object]"===l)n&&0!==Object.keys(e.dump).length?(!function(e,t,i,n){var o,r,s,a,l,c,d="",u=e.tag,h=Object.keys(i);if(!0===e.sortKeys)h.sort();else if("function"==typeof e.sortKeys)h.sort(e.sortKeys);else if(e.sortKeys)throw new Le("sortKeys must be a boolean or a function");for(o=0,r=h.length;o<r;o+=1)c="",n&&""===d||(c+=hi(e,t)),a=i[s=h[o]],e.replacer&&(a=e.replacer.call(i,s,a)),Ci(e,t+1,s,!0,!0,!0)&&((l=null!==e.tag&&"?"!==e.tag||e.dump&&e.dump.length>1024)&&(e.dump&&10===e.dump.charCodeAt(0)?c+="?":c+="? "),c+=e.dump,l&&(c+=hi(e,t)),Ci(e,t+1,a,!0,l)&&(e.dump&&10===e.dump.charCodeAt(0)?c+=":":c+=": ",d+=c+=e.dump));e.tag=u,e.dump=d||"{}"}(e,t,e.dump,o),u&&(e.dump="&ref_"+d+e.dump)):(!function(e,t,i){var n,o,r,s,a,l="",c=e.tag,d=Object.keys(i);for(n=0,o=d.length;n<o;n+=1)a="",""!==l&&(a+=", "),e.condenseFlow&&(a+='"'),s=i[r=d[n]],e.replacer&&(s=e.replacer.call(i,r,s)),Ci(e,t,r,!1,!1)&&(e.dump.length>1024&&(a+="? "),a+=e.dump+(e.condenseFlow?'"':"")+":"+(e.condenseFlow?"":" "),Ci(e,t,s,!1,!1)&&(l+=a+=e.dump));e.tag=c,e.dump="{"+l+"}"}(e,t,e.dump),u&&(e.dump="&ref_"+d+" "+e.dump));else if("[object Array]"===l)n&&0!==e.dump.length?(e.noArrayIndent&&!s&&t>0?ki(e,t-1,e.dump,o):ki(e,t,e.dump,o),u&&(e.dump="&ref_"+d+e.dump)):(!function(e,t,i){var n,o,r,s="",a=e.tag;for(n=0,o=i.length;n<o;n+=1)r=i[n],e.replacer&&(r=e.replacer.call(i,String(n),r)),(Ci(e,t,r,!1,!1)||void 0===r&&Ci(e,t,null,!1,!1))&&(""!==s&&(s+=","+(e.condenseFlow?"":" ")),s+=e.dump);e.tag=a,e.dump="["+s+"]"}(e,t,e.dump),u&&(e.dump="&ref_"+d+" "+e.dump));else{if("[object String]"!==l){if("[object Undefined]"===l)return!1;if(e.skipInvalid)return!1;throw new Le("unacceptable kind of an object to dump "+l)}"?"!==e.tag&&yi(e,e.dump,t,r,c)}null!==e.tag&&"?"!==e.tag&&(a=encodeURI("!"===e.tag[0]?e.tag.slice(1):e.tag).replace(/!/g,"%21"),a="!"===e.tag[0]?"!"+a:"tag:yaml.org,2002:"===a.slice(0,18)?"!!"+a.slice(18):"!<"+a+">",e.dump=a+" "+e.dump)}return!0}function Si(e,t){var i,n,o=[],r=[];for(Ei(e,o,r),i=0,n=r.length;i<n;i+=1)t.duplicates.push(o[r[i]]);t.usedDuplicates=new Array(n)}function Ei(e,t,i){var n,o,r;if(null!==e&&"object"==typeof e)if(-1!==(o=t.indexOf(e)))-1===i.indexOf(o)&&i.push(o);else if(t.push(e),Array.isArray(e))for(o=0,r=e.length;o<r;o+=1)Ei(e[o],t,i);else for(o=0,r=(n=Object.keys(e)).length;o<r;o+=1)Ei(e[n[o]],t,i)}var Oi=ii.load,Ti={dump:function(e,t){var i=new di(t=t||{});i.noRefs||Si(e,i);var n=e;return i.replacer&&(n=i.replacer.call({"":n},"",n)),Ci(i,0,n,!0,!0)?i.dump+"\n":""}}.dump;const Ii={condition:"state"};let Ni=class extends ae{constructor(){super(...arguments),this.value=[],this.disabled=!1,this.language="en",this._errors={},this._onAdd=()=>{this._emit([...this.value,{...Ii}])}}get hasError(){return Object.keys(this._errors).length>0}render(){return B`
      <div class="wrap">
        <div class="help">${fe(this.language,"conditions_help")}</div>
        ${this.value.map((e,t)=>this._row(e,t))}
        <button
          class="add-condition"
          ?disabled=${this.disabled}
          @click=${this._onAdd}
        >
          ${fe(this.language,"add_condition")}
        </button>
      </div>
    `}_row(e,t){const i=this._errors[t];return B`
      <div class="condition-row">
        <div class="body">
          <textarea
            .value=${Ti(e).trimEnd()}
            ?disabled=${this.disabled}
            @change=${e=>this._onEdit(e,t)}
          ></textarea>
          ${i?B`<div class="row-error">${i}</div>`:q}
        </div>
        <button
          class="remove-condition"
          ?disabled=${this.disabled}
          @click=${()=>this._onRemove(t)}
        >
          ${fe(this.language,"remove_condition")}
        </button>
      </div>
    `}_emit(e){this.dispatchEvent(new CustomEvent("condition-changed",{detail:{value:e}}))}_setError(e,t){const i={...this._errors};null===t?delete i[e]:i[e]=t,this._errors=i}_onEdit(e,t){const i=e.target.value;let n;try{n=Oi(i)}catch{return void this._setError(t,fe(this.language,"condition_unparseable"))}if(null===n||"object"!=typeof n||Array.isArray(n))return void this._setError(t,fe(this.language,"condition_not_a_mapping"));this._setError(t,null);const o=[...this.value];o[t]=n,this._emit(o)}_onRemove(e){const t={};for(const[i,n]of Object.entries(this._errors)){const o=Number(i);o<e?t[o]=n:o>e&&(t[o-1]=n)}this._errors=t,this._emit(this.value.filter((t,i)=>i!==e))}};Ni.styles=s`
    .condition-row {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      margin-block: 8px;
    }
    textarea {
      font-family: var(--code-font-family, monospace);
      font-size: 0.85em;
      flex: 1;
      min-inline-size: 0;
      min-block-size: 4.5em;
      padding: 6px;
    }
    .row-error {
      color: var(--error-color, #d64545);
      font-size: 0.8em;
      margin-block-start: 2px;
    }
    .body { flex: 1; min-inline-size: 0; }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    button {
      font: inherit;
      padding-block: 4px;
      padding-inline: 8px;
      border-radius: 6px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  `,e([he({attribute:!1})],Ni.prototype,"value",void 0),e([he({type:Boolean})],Ni.prototype,"disabled",void 0),e([he()],Ni.prototype,"language",void 0),e([pe()],Ni.prototype,"_errors",void 0),Ni=e([ce("shabbat-condition-editor")],Ni);let ji=class extends ae{constructor(){super(...arguments),this.hass=null,this.value={enabled:!1},this.disabled=!1,this.language="en",this._onEnabled=e=>{const t=Boolean(e.detail?.value);this._emit(t?{enabled:!0,within:this.value.within??"01:00:00"}:{enabled:!1})},this._onWithin=e=>{const t=e.detail?.value;var i;this._emit(void 0===t?{enabled:!0}:{enabled:!0,within:(i=t,[i?.hours??0,i?.minutes??0,i?.seconds??0].map(e=>String(e).padStart(2,"0")).join(":"))})}}render(){return B`
      <div class="wrap">
        <div class="field">
          <label for="replay-enabled">
            ${fe(this.language,"replay_after_restart")}
          </label>
          <ha-selector
            id="replay-enabled"
            class="replay-enabled"
            .hass=${this.hass}
            .selector=${{boolean:{}}}
            .value=${this.value.enabled}
            .disabled=${this.disabled}
            @value-changed=${this._onEnabled}
          ></ha-selector>
        </div>
        ${this.value.enabled?B`<div class="field">
              <label for="replay-within">
                ${fe(this.language,"replay_within_label")}
              </label>
              <ha-selector
                id="replay-within"
                class="replay-within"
                .hass=${this.hass}
                .selector=${{duration:{}}}
                .value=${function(e){if(void 0===e)return;const t=e.split(":");if(3!==t.length)return;if(!t.every(e=>/^\d+$/.test(e)))return;const[i,n,o]=t.map(e=>Number(e));return{hours:i,minutes:n,seconds:o}}(this.value.within)}
                .disabled=${this.disabled}
                @value-changed=${this._onWithin}
              ></ha-selector>
            </div>`:B`<div class="help">${fe(this.language,"replay_help")}</div>`}
      </div>
    `}_emit(e){this.dispatchEvent(new CustomEvent("replay-changed",{detail:{value:e}}))}};ji.styles=s`
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
  `,e([he({attribute:!1})],ji.prototype,"hass",void 0),e([he({attribute:!1})],ji.prototype,"value",void 0),e([he({type:Boolean})],ji.prototype,"disabled",void 0),e([he()],ji.prototype,"language",void 0),ji=e([ce("shabbat-replay-editor")],ji);let Mi=class extends ae{constructor(){super(...arguments),this.hass=null,this.action="",this.data={},this.target=null,this.disabled=!1,this._onChange=e=>{const t=e.detail?.value??{},i={action:"string"==typeof t.action?t.action:""};"object"==typeof t.data&&null!==t.data&&(i.data=t.data),this.dispatchEvent(new CustomEvent("service-changed",{detail:i}))},this._observer=null}render(){return B`
      <div class="wrap">
        <!-- No \`showAdvanced\`. It was passed here for a while, first
             hard-coded true and then following the user's own preference -
             but \`ha-service-control\` has no such property in this Home
             Assistant version. Its full property list is \`hass, value,
             disabled, narrow, showServiceId, hidePicker, hideDescription\`,
             so the binding was inert and the tests asserting it only
             passed because happy-dom accepts any property on an element it
             has never heard of. Which advanced fields render is HA's
             decision, made inside its own element. -->
        <ha-service-control
          .hass=${this.hass}
          .value=${this.target&&Object.keys(this.target).length?{action:this.action,target:this.target,data:this.data}:{action:this.action,data:this.data}}
          .disabled=${this.disabled}
          @value-changed=${this._onChange}
        ></ha-service-control>
      </div>
    `}get _control(){return this.shadowRoot?.querySelector("ha-service-control")??null}async updated(){const e=this._control;e?.updateComplete&&await e.updateComplete,this.suppressTargetRows(),this._watch()}disconnectedCallback(){super.disconnectedCallback(),this._observer?.disconnect(),this._observer=null}_watch(){const e=this._control?.shadowRoot;!this._observer&&e&&(this._observer=new MutationObserver(()=>this.suppressTargetRows()),this._observer.observe(e,{childList:!0}))}suppressTargetRows(){const e=this._control?.shadowRoot;if(!e)return 0;const t=[...e.querySelectorAll("ha-selector")].filter(e=>{const t=e.selector;return"object"==typeof t&&null!==t&&"target"in t});for(const e of t)e.style.setProperty("display","none","important");return this.setAttribute("data-target-rows-suppressed",String(t.length)),t.length}};Mi.styles=s`
    :host { display: block; }
  `,e([he({attribute:!1})],Mi.prototype,"hass",void 0),e([he()],Mi.prototype,"action",void 0),e([he({attribute:!1})],Mi.prototype,"data",void 0),e([he({attribute:!1})],Mi.prototype,"target",void 0),e([he({type:Boolean})],Mi.prototype,"disabled",void 0),Mi=e([ce("shabbat-service-editor")],Mi);let Ri=class extends ae{constructor(){super(...arguments),this.hass=null,this.value={},this.inherited={},this.disabled=!1,this.language="en",this._onChange=e=>{const t=e.detail?.value??{};this.dispatchEvent(new CustomEvent("target-changed",{detail:{value:t}}))}}render(){const e=$e(this.value,this.hass),t=$e(this.inherited,this.hass),i=""===e&&""!==t;return B`
      <div class="wrap">
        <ha-selector
          .hass=${this.hass}
          .selector=${{target:{}}}
          .value=${this.value}
          .disabled=${this.disabled}
          @value-changed=${this._onChange}
        ></ha-selector>
        ${i?B`<div class="note inherited">
              ${fe(this.language,"inherits_target_from_defaults")}
              ${t}
            </div>`:""===e?B`<div class="note empty">${fe(this.language,"target_none")}</div>`:q}
      </div>
    `}};Ri.styles=s`
    .note {
      color: var(--secondary-text-color, #666);
      font-size: 0.85em;
      margin-block-start: 4px;
      overflow-wrap: anywhere;
    }
  `,e([he({attribute:!1})],Ri.prototype,"hass",void 0),e([he({attribute:!1})],Ri.prototype,"value",void 0),e([he({attribute:!1})],Ri.prototype,"inherited",void 0),e([he({type:Boolean})],Ri.prototype,"disabled",void 0),e([he()],Ri.prototype,"language",void 0),Ri=e([ce("shabbat-target-editor")],Ri);const Pi={day:"erev",time:"",action:"",target:{},data:{},condition:[],replay:{enabled:!1},name:null,icon:null,color:null,enabled:!0};let zi=class extends ae{constructor(){super(...arguments),this.hass=null,this.rule=null,this.seed=null,this.day="erev",this.profile=1,this.defaults={},this.canWrite=!1,this.busy=!1,this.error=null,this.language="en",this.runNowResult=null,this._form=Pi,this._advanced=!1,this._conditionError=!1,this._runConfirmOpen=!1,this._seeded=null}willUpdate(){const e=this.rule?`edit:${this.rule.id}`:`new:${this.day}:${this.profile}:${JSON.stringify(this.seed)}`;var t;this._seeded!==e&&(this._seeded=e,this.rule?this._form={day:(t=this.rule).day,time:t.time,action:t.action,target:{...t.target},data:{...t.data},condition:t.condition.map(e=>({...e})),replay:{...t.replay},name:t.name,icon:t.icon,color:t.color,enabled:t.enabled}:this.seed?this._form={...this.seed,day:this.day}:this._form={...Pi,day:this.day},this._advanced=!1,this._runConfirmOpen=!1)}updated(){const e=this.shadowRoot?.querySelector("select.day");e&&e.value!==this._form.day&&(e.value=this._form.day)}_patch(e){this._form={...this._form,...e},this._runConfirmOpen=!1}get _dirty(){return null!==this.rule&&Object.keys(Te(this._form,this.rule)).length>0}_emit(e){this.dispatchEvent(new CustomEvent(e,{detail:{form:this._form,rule:this.rule}}))}_text(e,t){return B`
      <div class="field">
        <label for=${e}>${t}</label>
        <input
          id=${e}
          class=${e}
          .value=${String(this._form[e]??"")}
          ?disabled=${!this.canWrite}
          @change=${t=>{const i=t.target.value;this._patch({[e]:""===i?null:i})}}
        />
      </div>
    `}_timeField(){return B`
      <div class="field">
        <label for="time">${fe(this.language,"time")}</label>
        <ha-selector
          id="time"
          class="time"
          .hass=${this.hass}
          .selector=${{time:{}}}
          .value=${this._form.time||null}
          .disabled=${!this.canWrite}
          @value-changed=${e=>this._patch({time:e.detail?.value??""})}
        ></ha-selector>
      </div>
    `}_dayField(){const e=be(this.rule?.profile??this.profile);return e.includes(this._form.day)||e.push(this._form.day),B`
      <div class="field">
        <label for="day">${fe(this.language,"day")}</label>
        <select
          id="day"
          class="day"
          ?disabled=${!this.canWrite}
          @change=${e=>this._patch({day:e.target.value})}
        >
          ${e.map(e=>B`<option value=${e} ?selected=${e===this._form.day}>
              ${we(e,this.language)}
            </option>`)}
        </select>
      </div>
    `}_enabledField(){return B`
      <div class="field inline">
        <label for="enabled">${fe(this.language,"enabled")}</label>
        <ha-selector
          id="enabled"
          class="enabled"
          .hass=${this.hass}
          .selector=${{boolean:{}}}
          .value=${this._form.enabled}
          .disabled=${!this.canWrite}
          @value-changed=${e=>this._patch({enabled:Boolean(e.detail?.value)})}
        ></ha-selector>
      </div>
    `}_iconField(){return B`
      <div class="field">
        <label for="icon">${fe(this.language,"icon")}</label>
        <ha-selector
          id="icon"
          class="icon"
          .hass=${this.hass}
          .selector=${{icon:{}}}
          .value=${this._form.icon??""}
          .disabled=${!this.canWrite}
          @value-changed=${e=>{const t=e.detail?.value??"";this._patch({icon:""===t?null:t})}}
        ></ha-selector>
      </div>
    `}_colorField(){return B`
      <div class="field inline">
        <label for="color">${fe(this.language,"colour")}</label>
        <input
          id="color"
          class="color"
          type="color"
          .value=${this._form.color||"#000000"}
          ?disabled=${!this.canWrite}
          @change=${e=>{this._patch({color:e.target.value})}}
        />
      </div>
    `}_onSave(){const e=this.shadowRoot?.querySelector("shabbat-condition-editor");e?.hasError?this._conditionError=!0:(this._conditionError=!1,this._emit("dialog-save"))}_emitRunNow(e){this._runConfirmOpen=!1,this.dispatchEvent(new CustomEvent("dialog-run-now",{detail:{rule:this.rule,simulate:e}}))}render(){const e=null!==this.rule;return B`
      <div class="sheet" @click=${e=>{e.target===e.currentTarget&&this.dispatchEvent(new CustomEvent("dialog-close"))}}>
        <div class="panel">
          <div class="head">
            <h2>${fe(this.language,e?"edit_rule":"add_rule")}</h2>
          </div>
          <div class="content">

          ${this.canWrite?q:B`<div class="note">${fe(this.language,"read_only")}</div>`}
          ${null!==this.error?B`<div class="error">${this.error}</div>`:q}
          ${this._conditionError?B`<div class="error condition-blocked">
                ${fe(this.language,"condition_unparseable")}
              </div>`:q}

          <div class="form">
            <div class="section">
              ${this._text("name",fe(this.language,"name"))}
              <div class="when">
                ${this._dayField()}
                ${this._timeField()}
              </div>
            </div>

            <div class="section">
            <h3 class="section-title">${fe(this.language,"section_action")}</h3>

            <!-- \`data: … ?? {}\` below is on purpose, and it must NOT
                 become "preserve the old data" the way the defaults
                 dialog's handler does. HA omits \`data\` from the event on
                 every service change; for a RULE the action is part of the
                 rule, so data shaped for the service the author just
                 navigated away from does not belong to the new one, and
                 clearing it is Home Assistant's own semantics. See
                 \`service-editor.ts\`'s \`_onChange\` for why the two cases
                 are distinguishable at all. -->
            <shabbat-service-editor
              .hass=${this.hass}
              .action=${this._form.action}
              .target=${Object.keys(this._form.target??{}).length?this._form.target:this.defaults.target??{}}
              .data=${this._form.data}
              .disabled=${!this.canWrite}
              @service-changed=${e=>this._patch({action:e.detail.action,data:e.detail.data??{}})}
            ></shabbat-service-editor>

            <shabbat-target-editor
              .hass=${this.hass}
              .value=${this._form.target}
              .inherited=${this.defaults.target??{}}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @target-changed=${e=>this._patch({target:e.detail.value})}
            ></shabbat-target-editor>
            </div>

            <div class="section">
            <h3 class="section-title">${fe(this.language,"section_conditions")}</h3>

            <shabbat-condition-editor
              .value=${this._form.condition}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @condition-changed=${e=>{const t=e.target;this._conditionError=!0===t.hasError,this._patch({condition:e.detail.value})}}
            ></shabbat-condition-editor>
            </div>

            <div class="section">
            <h3 class="section-title">${fe(this.language,"section_options")}</h3>
            ${this._enabledField()}

            <shabbat-replay-editor
              .hass=${this.hass}
              .value=${this._form.replay}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @replay-changed=${e=>this._patch({replay:e.detail.value})}
            ></shabbat-replay-editor>

            <button
              class="advanced-toggle"
              @click=${()=>{this._advanced=!this._advanced}}
            >
              ${fe(this.language,"advanced")}
            </button>
            ${this._advanced?B`
                  <div class="advanced">
                    ${this._iconField()}
                    ${this._colorField()}
                  </div>
                `:q}
            </div>
          </div>
          </div>

          <div class="foot">
          ${this._runConfirmOpen?B`<div class="run-confirm">
                <button
                  class="run-simulate"
                  ?disabled=${this._dirty}
                  @click=${()=>this._emitRunNow(!0)}
                >${fe(this.language,"run_now_simulate")}</button>
                <button
                  class="run-real"
                  ?disabled=${this._dirty}
                  @click=${()=>this._emitRunNow(!1)}
                >${fe(this.language,"run_now_real")}</button>
              </div>`:q}
          ${null===this.rule||this._dirty||this.runNowResult?.ruleId!==this.rule.id?q:B`<div class="run-now-result">
                ${(t=this.runNowResult,i=this.language,[Ae(Se(t.results,t.at),i)]).map(e=>B`<div>${e}</div>`)}
              </div>`}
          <div class="actions">
            ${this.canWrite&&e?B`<button
                  class="delete"
                  ?disabled=${this.busy}
                  @click=${()=>this._emit("dialog-delete")}
                >
                  ${fe(this.language,"delete_rule")}
                </button>`:q}
            ${this.canWrite&&e?B`<button
                  class="duplicate"
                  ?disabled=${this.busy}
                  @click=${()=>this._emit("dialog-duplicate")}
                >
                  ${fe(this.language,"duplicate")}
                </button>`:q}
            ${this.canWrite&&e?B`<button
                  class="run-now"
                  ?disabled=${this.busy||this._dirty}
                  title=${this._dirty?fe(this.language,"run_now_disabled_dirty"):""}
                  @click=${()=>{this._runConfirmOpen=!this._runConfirmOpen}}
                >
                  ▶ ${fe(this.language,"run_now_button")}
                </button>`:q}
            <span class="spacer"></span>
            <button @click=${()=>this.dispatchEvent(new CustomEvent("dialog-close"))}>
              ${fe(this.language,"cancel")}
            </button>
            ${this.canWrite?B`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${()=>this._onSave()}
                >
                  ${fe(this.language,"save")}
                </button>`:q}
          </div>
          </div>
        </div>
      </div>
    `;var t,i}};zi.styles=s`
    .sheet {
      position: fixed;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.4);
      z-index: 10;
    }
    /* Header, scrolling content, footer: the title and the Save button
       stay put however long the form gets. */
    .panel {
      display: flex;
      flex-direction: column;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px;
      inline-size: min(30rem, 94vw);
      max-block-size: 90vh;
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }
    .head {
      padding-block: 16px 8px;
      padding-inline: 20px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    h2 { margin: 0; font-size: 1.2em; font-weight: 500; }
    .content {
      flex: 1;
      min-block-size: 0;
      overflow: auto;
      padding-block: 4px 16px;
      padding-inline: 20px;
    }
    .section { padding-block: 12px; }
    .section + .section { border-block-start: 1px solid var(--divider-color, #e0e0e0); }
    .section-title {
      margin-block: 0 8px;
      font-size: 0.75em;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--secondary-text-color, #666);
    }
    /* Label above its control: no 7em label column eating a phone's
       width. Toggles are the exception - label left, switch right. */
    .field { display: flex; flex-direction: column; gap: 4px; margin-block: 8px; }
    .field label { font-size: 0.85em; color: var(--secondary-text-color, #666); }
    .field.inline { flex-direction: row; align-items: center; justify-content: space-between; }
    .field.inline label { font-size: 1em; color: inherit; }
    /* Day and time side by side - together they ARE "when". */
    .when {
      display: grid;
      grid-template-columns: minmax(6.5em, 1fr) auto;
      gap: 12px;
      align-items: end;
    }
    .when .field { margin-block: 0; }
    /* Match Home Assistant's own text field height, so the select and
       the time picker beside it line up. */
    .when select { min-block-size: 56px; }
    input, select {
      font: inherit;
      box-sizing: border-box;
      min-block-size: 40px;
      padding-block: 6px;
      padding-inline: 10px;
      border: 1px solid var(--divider-color, #c8c8c8);
      border-radius: 8px;
      background: var(--card-background-color, #fff);
      color: inherit;
      inline-size: 100%;
      min-inline-size: 0;
    }
    input[type='color'] { padding: 2px; inline-size: 4em; }
    .foot {
      border-block-start: 1px solid var(--divider-color, #e0e0e0);
      padding-block: 10px;
      padding-inline: 16px;
      background: var(--card-background-color, #fff);
    }
    .actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    /* Secondary actions are quiet text buttons on the start side; Cancel
       and Save sit together at the end, Save the only filled one. */
    .actions .spacer { flex: 1; }
    .actions .delete, .actions .duplicate, .actions .run-now {
      border-color: transparent;
      background: none;
      padding-inline: 8px;
    }
    .actions .delete { color: var(--error-color, #d64545); }
    .actions .save {
      background: var(--primary-color, #03a9f4);
      border-color: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      font-weight: 500;
    }
    button {
      font: inherit;
      min-block-size: 36px;
      padding-block: 6px;
      padding-inline: 14px;
      border-radius: 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    .run-confirm { display: flex; gap: 8px; margin-block-start: 8px; flex-wrap: wrap; }
    .run-now-result { font-size: 0.9em; margin-block-start: 8px; }
    .error {
      color: var(--error-color, #d64545);
      margin-block: 8px;
      font-size: 0.9em;
    }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; margin-block: 8px; }
    /* The wrapper around the advanced fields is load-bearing under this
       repo's pinned lit-html + happy-dom: a template whose root holds
       several top-level expressions renders NONE of them. Same constraint
       day-group.ts documents. Do not unwrap it. */
    .advanced { display: contents; }
    .advanced-toggle {
      background: none;
      border: none;
      padding-inline: 0;
      color: var(--primary-color, #03a9f4);
    }
    /* A phone: the dialog IS the screen. */
    @media (max-width: 600px) {
      .sheet { align-items: stretch; }
      .panel {
        inline-size: 100vw;
        max-block-size: none;
        block-size: 100%;
        border-radius: 0;
      }
      .head { padding-inline: 16px; }
      .content { padding-inline: 16px; }
      .foot { padding-block-end: max(10px, env(safe-area-inset-bottom)); }
      /* Secondary actions on their own row, primary row full width. */
      .actions .spacer { flex-basis: 100%; block-size: 0; }
      .actions button:not(.delete):not(.duplicate):not(.run-now) { flex: 1; }
    }
  `,e([he({attribute:!1})],zi.prototype,"hass",void 0),e([he({attribute:!1})],zi.prototype,"rule",void 0),e([he({attribute:!1})],zi.prototype,"seed",void 0),e([he()],zi.prototype,"day",void 0),e([he({type:Number})],zi.prototype,"profile",void 0),e([he({attribute:!1})],zi.prototype,"defaults",void 0),e([he({type:Boolean})],zi.prototype,"canWrite",void 0),e([he({type:Boolean})],zi.prototype,"busy",void 0),e([he()],zi.prototype,"error",void 0),e([he()],zi.prototype,"language",void 0),e([he({attribute:!1})],zi.prototype,"runNowResult",void 0),e([pe()],zi.prototype,"_form",void 0),e([pe()],zi.prototype,"_advanced",void 0),e([pe()],zi.prototype,"_conditionError",void 0),e([pe()],zi.prototype,"_runConfirmOpen",void 0),zi=e([ce("shabbat-rule-dialog")],zi);let Di=class extends ae{constructor(){super(...arguments),this.hass=null,this.defaults={},this.canWrite=!1,this.busy=!1,this.error=null,this.language="en",this.languageOverride=null,this._draft={},this._action="",this._seeded=!1,this._onServiceChanged=e=>{const t=e.detail;this._action="string"==typeof t.action?t.action:"","data"in t&&(this._draft={...this._draft,data:t.data})},this._onLanguageChanged=e=>{const t=e.detail?.value;this.dispatchEvent(new CustomEvent("language-changed",{detail:{language:t||null}}))}}willUpdate(){this._seeded||(this._seeded=!0,this._draft={target:this.defaults.target??{},data:this.defaults.data??{}})}_onSave(){this.dispatchEvent(new CustomEvent("dialog-save",{detail:{defaults:{target:this._draft.target??{},data:this._draft.data??{}}}}))}render(){return B`
      <div class="sheet" @click=${e=>{e.target===e.currentTarget&&this.dispatchEvent(new CustomEvent("dialog-close"))}}>
        <div class="panel">
          <h2>${fe(this.language,"defaults_title")}</h2>
          <div class="note">${fe(this.language,"defaults_help")}</div>
          ${null!==this.error?B`<div class="error">${this.error}</div>`:q}

          <div class="section">
            <div class="label">${fe(this.language,"card_language")}</div>
            <ha-selector
              .hass=${this.hass}
              .selector=${{select:{mode:"dropdown",options:[{value:"",label:fe(this.language,"card_language_auto")},{value:"en",label:"English"},{value:"he",label:"עברית"}]}}}
              .value=${this.languageOverride??""}
              .disabled=${!this.canWrite}
              @value-changed=${this._onLanguageChanged}
            ></ha-selector>
          </div>

          <div class="form">
            <div class="section">
              <div class="label">${fe(this.language,"target")}</div>
              <shabbat-target-editor
                .hass=${this.hass}
                .value=${this._draft.target??{}}
                .disabled=${!this.canWrite}
                .language=${this.language}
                @target-changed=${e=>{this._draft={...this._draft,target:e.detail.value}}}
              ></shabbat-target-editor>
            </div>
            <div class="section">
              <div class="label">${fe(this.language,"data")}</div>
              <shabbat-service-editor
                .hass=${this.hass}
                .action=${this._action}
                .target=${this._draft.target??{}}
                .data=${this._draft.data??{}}
                .disabled=${!this.canWrite}
                @service-changed=${this._onServiceChanged}
              ></shabbat-service-editor>
            </div>
          </div>

          <div class="actions">
            <button @click=${()=>this.dispatchEvent(new CustomEvent("dialog-close"))}>
              ${fe(this.language,"cancel")}
            </button>
            ${this.canWrite?B`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${()=>this._onSave()}
                >
                  ${fe(this.language,"save")}
                </button>`:q}
          </div>
        </div>
      </div>
    `}};Di.styles=s`
    .sheet {
      position: fixed;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.4);
      z-index: 10;
    }
    .panel {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px;
      padding: 16px;
      inline-size: min(28rem, 92vw);
      max-block-size: 88vh;
      overflow: auto;
    }
    h2 { margin-block: 0 4px; font-size: 1.1em; }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    .section { margin-block: 12px; }
    .section .label { color: var(--secondary-text-color, #666); font-size: 0.85em; margin-block-end: 4px; }
    .actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      margin-block-start: 16px;
    }
    button {
      font: inherit;
      padding-block: 6px;
      padding-inline: 12px;
      border-radius: 6px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  `,e([he({attribute:!1})],Di.prototype,"hass",void 0),e([he({attribute:!1})],Di.prototype,"defaults",void 0),e([he({type:Boolean})],Di.prototype,"canWrite",void 0),e([he({type:Boolean})],Di.prototype,"busy",void 0),e([he()],Di.prototype,"error",void 0),e([he()],Di.prototype,"language",void 0),e([he()],Di.prototype,"languageOverride",void 0),e([pe()],Di.prototype,"_draft",void 0),e([pe()],Di.prototype,"_action",void 0),Di=e([ce("shabbat-defaults-dialog")],Di);let Wi=class extends ae{constructor(){super(...arguments),this.hass=null,this.language="en",this.canWrite=!1,this._profile=1,this._day="erev",this._forceConditions=!1,this._preview=null,this._busy=!1,this._error=null,this._results=null,this._runRealConfirmOpen=!1}connectedCallback(){super.connectedCallback(),this._loadPreview()}async _loadPreview(){if(null!==this.hass){this._busy=!0;try{this._preview=await this.hass.callWS({type:"shabbat_scheduler/preview",block_length:this._profile})}catch(e){const t=e;this._error=t?.message??String(e)}finally{this._busy=!1}}}_previewRules(){return(this._preview?.rules??[]).filter(e=>void 0===e.day||e.day===this._day)}_label(e){const t=(this._preview?.rules??[]).find(t=>t.rule_id===e);return void 0===t?e:t.name??t.action}async _run(e){if(null!==this.hass){this._runRealConfirmOpen=!1,this._busy=!0,this._error=null;try{const t=await this.hass.callWS({type:"shabbat_scheduler/rules/run_day",profile:this._profile,day:this._day,simulate:e,force_conditions:this._forceConditions});this._results=t.results.map(e=>({ruleId:e.rule_id,results:e.results}))}catch(e){const t=e;this._error=t?.message??String(e)}finally{this._busy=!1}}}_dayLabel(e){return"erev"===e?fe(this.language,"erev"):`${fe(this.language,"day")} ${e}`}render(){return B`
      <div class="sheet" @click=${e=>{e.target===e.currentTarget&&this.dispatchEvent(new CustomEvent("dialog-close"))}}>
        <div class="panel">
          <h2>${fe(this.language,"simulate_title")}</h2>
          ${null!==this._error?B`<div class="error">${this._error}</div>`:q}

          <div class="field">
            <label>${fe(this.language,"simulate_profile")}</label>
            <select
              class="profile"
              .value=${String(this._profile)}
              @change=${e=>{this._profile=Number(e.target.value),be(this._profile).includes(this._day)||(this._day="erev"),this._runRealConfirmOpen=!1,this._loadPreview()}}
            >
              ${[1,2,3].map(e=>B`<option value=${e}>${e}d</option>`)}
            </select>
          </div>
          <div class="field">
            <label>${fe(this.language,"simulate_day")}</label>
            <select
              class="day"
              .value=${this._day}
              @change=${e=>{this._day=e.target.value,this._runRealConfirmOpen=!1}}
            >
              ${be(this._profile).map(e=>B`<option value=${e}>${this._dayLabel(e)}</option>`)}
            </select>
          </div>
          <div class="field">
            <label>${fe(this.language,"simulate_force_conditions")}</label>
            <ha-selector
              class="force-conditions"
              .hass=${this.hass}
              .selector=${{boolean:{}}}
              .value=${this._forceConditions}
              .disabled=${!this.canWrite}
              @value-changed=${e=>{this._forceConditions=Boolean(e.detail?.value)}}
            ></ha-selector>
          </div>

          ${null!==this._preview?B`<div class="preview">
                ${this._previewRules().map(e=>B`<div class="row">
                    ${e.when.slice(11,16)} — ${e.name??e.action}
                  </div>`)}
              </div>`:q}

          ${null!==this._results?B`<div class="results">
                ${this._results.map(e=>{const t=Se(e.results,(new Date).toISOString());return B`<div class="row">
                    ${this._label(e.ruleId)}: ${Ae(t,this.language)}
                  </div>`})}
              </div>`:q}

          <div class="actions">
            <button @click=${()=>this.dispatchEvent(new CustomEvent("dialog-close"))}>
              ${fe(this.language,"cancel")}
            </button>
            ${this.canWrite?B`<button
                  class="run-simulate"
                  ?disabled=${this._busy}
                  @click=${()=>this._run(!0)}
                >${fe(this.language,"simulate_this_day")}</button>
                <button
                  class="run-real"
                  ?disabled=${this._busy}
                  @click=${()=>{this._runRealConfirmOpen=!this._runRealConfirmOpen}}
                >${fe(this.language,"simulate_run_for_real")}</button>`:q}
          </div>
          ${this._runRealConfirmOpen?B`<div class="run-real-confirm">
                <div class="confirm-text">
                  ${fe(this.language,"simulate_run_for_real_confirm")} ${this._dayLabel(this._day)}.
                </div>
                <button
                  class="run-real-cancel"
                  @click=${()=>{this._runRealConfirmOpen=!1}}
                >${fe(this.language,"cancel")}</button>
                <button
                  class="run-real-confirmed"
                  ?disabled=${this._busy}
                  @click=${()=>this._run(!1)}
                >${fe(this.language,"run_now_real")}</button>
              </div>`:q}
        </div>
      </div>
    `}};Wi.styles=s`
    .sheet {
      position: fixed; inset: 0; display: flex; align-items: center;
      justify-content: center; background: rgba(0, 0, 0, 0.4); z-index: 10;
    }
    .panel {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px; padding: 16px;
      inline-size: min(28rem, 92vw); max-block-size: 88vh; overflow: auto;
    }
    h2 { margin-block: 0 12px; font-size: 1.1em; }
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    select { font: inherit; padding-block: 4px; padding-inline: 6px; flex: 1; }
    .row {
      padding-block: 4px; font-size: 0.9em;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    .actions {
      display: flex; gap: 8px; justify-content: flex-end;
      flex-wrap: wrap; margin-block-start: 16px;
    }
    button {
      font: inherit; padding-block: 6px; padding-inline: 12px;
      border-radius: 6px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); color: inherit; cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  `,e([he({attribute:!1})],Wi.prototype,"hass",void 0),e([he()],Wi.prototype,"language",void 0),e([he({type:Boolean})],Wi.prototype,"canWrite",void 0),e([pe()],Wi.prototype,"_profile",void 0),e([pe()],Wi.prototype,"_day",void 0),e([pe()],Wi.prototype,"_forceConditions",void 0),e([pe()],Wi.prototype,"_preview",void 0),e([pe()],Wi.prototype,"_busy",void 0),e([pe()],Wi.prototype,"_error",void 0),e([pe()],Wi.prototype,"_results",void 0),e([pe()],Wi.prototype,"_runRealConfirmOpen",void 0),Wi=e([ce("shabbat-simulate-dialog")],Wi);let Li=class extends ae{constructor(){super(...arguments),this.source=null,this.rules=[],this.canWrite=!1,this.busy=!1,this.error=null,this.landed=null,this.failed=null,this.language="en",this._targetProfile=1,this._targetDay="erev",this._mode="extend",this._seeded=null,this._nameById=new Map}willUpdate(){const e=this.source?`${this.source.scope}:${this.source.profile}:${this.source.day??""}`:null;e!==this._seeded&&(this._seeded=e,this._targetProfile=this.source?.profile??1,this._targetDay=this.source?.day??"erev",this._mode="extend")}get _dayScope(){return"day"===this.source?.scope}_sourceRuleIds(){return null===this.source?[]:this._dayScope?this.rules.filter(e=>e.profile===this.source.profile&&e.day===this.source.day).map(e=>e.id):this.rules.filter(e=>e.profile===this.source.profile).map(e=>e.id)}_idsToSend(){return null!==this.failed&&this.failed.length>0?this.failed:this._sourceRuleIds()}_targetRuleCount(){return this._dayScope?this.rules.filter(e=>e.profile===this._targetProfile&&e.day===this._targetDay).length:this.rules.filter(e=>e.profile===this._targetProfile).length}_title(){if(null===this.source)return"";if(this._dayScope){const e="erev"===this.source.day?fe(this.language,"erev"):`${fe(this.language,"day")} ${this.source.day}`;return`${fe(this.language,"clone_day_prefix")} ${e}`}return`${fe(this.language,"clone_profile_prefix")} ${this.source.profile}${fe(this.language,"clone_profile_suffix")}`}_label(e){return this._nameById.get(e)??e}_onConfirm(){const e=this._idsToSend();for(const t of e){const e=this.rules.find(e=>e.id===t);e&&this._nameById.set(t,e.name??e.action)}this.dispatchEvent(new CustomEvent("dialog-clone-confirm",{detail:{sourceRuleIds:e,sourceProfile:this.source?.profile,sourceScope:this.source?.scope,targetProfile:this._targetProfile,targetDay:this._dayScope?this._targetDay:void 0,mode:this._mode}}))}render(){if(null===this.source)return q;const e=0===this._idsToSend().length,t=this._targetRuleCount();return B`
      <div class="sheet" @click=${e=>{e.target===e.currentTarget&&this.dispatchEvent(new CustomEvent("dialog-close"))}}>
        <div class="panel">
          <h2>${this._title()}</h2>
          ${this.canWrite?q:B`<div class="note">${fe(this.language,"read_only")}</div>`}
          ${null!==this.error?B`<div class="error">${this.error}</div>`:q}
          ${null!==this.landed?B`<div class="report">
                ${fe(this.language,"clone_landed")}: ${this.landed.map(e=>this._label(e)).join(", ")||fe(this.language,"clone_none")}
                ${this.failed&&this.failed.length?B`<div class="failed-line">
                      ${fe(this.language,"clone_failed")}: ${this.failed.map(e=>this._label(e)).join(", ")}
                    </div>`:q}
              </div>`:q}

          <div class="field">
            <label>${fe(this.language,"clone_target_profile")}</label>
            <select
              class="target-profile"
              .value=${String(this._targetProfile)}
              ?disabled=${!this.canWrite}
              @change=${e=>{this._targetProfile=Number(e.target.value),this._dayScope&&!be(this._targetProfile).includes(this._targetDay)&&(this._targetDay="erev")}}
            >
              ${[1,2,3].map(e=>B`<option value=${e}>${e}d</option>`)}
            </select>
          </div>
          ${this._dayScope?B`<div class="field">
                <label>${fe(this.language,"clone_target_day")}</label>
                <select
                  class="target-day"
                  .value=${this._targetDay}
                  ?disabled=${!this.canWrite}
                  @change=${e=>{this._targetDay=e.target.value}}
                >
                  ${be(this._targetProfile).map(e=>B`<option value=${e}>
                      ${"erev"===e?fe(this.language,"erev"):`${fe(this.language,"day")} ${e}`}
                    </option>`)}
                </select>
              </div>`:q}

          <div class="field">
            <button
              class="mode extend ${"extend"===this._mode?"active":""}"
              ?disabled=${!this.canWrite}
              @click=${()=>{this._mode="extend"}}
            >${fe(this.language,"clone_extend")}</button>
            <button
              class="mode overwrite ${"overwrite"===this._mode?"active":""}"
              ?disabled=${!this.canWrite}
              @click=${()=>{this._mode="overwrite"}}
            >${fe(this.language,"clone_overwrite")}</button>
          </div>

          ${t>0?B`<div class="warning">${fe(this.language,"clone_target_has_rules")} ${t}</div>`:q}

          <div class="actions">
            <button @click=${()=>this.dispatchEvent(new CustomEvent("dialog-close"))}>
              ${fe(this.language,"cancel")}
            </button>
            ${this.canWrite?B`<button
                  class="confirm"
                  ?disabled=${this.busy||e}
                  @click=${()=>this._onConfirm()}
                >${fe(this.language,"clone_confirm")}</button>`:q}
          </div>
        </div>
      </div>
    `}};Li.styles=s`
    .sheet {
      position: fixed; inset: 0; display: flex; align-items: center;
      justify-content: center; background: rgba(0, 0, 0, 0.4); z-index: 10;
    }
    .panel {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px; padding: 16px;
      inline-size: min(28rem, 92vw); max-block-size: 88vh; overflow: auto;
    }
    h2 { margin-block: 0 12px; font-size: 1.1em; }
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 7em; }
    select { font: inherit; padding-block: 4px; padding-inline: 6px; flex: 1; }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    .warning { color: var(--warning-color, #d9822b); margin-block: 8px; font-size: 0.9em; }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    .report { font-size: 0.85em; margin-block: 8px; }
    .actions {
      display: flex; gap: 8px; justify-content: flex-end;
      margin-block-start: 16px; flex-wrap: wrap;
    }
    button {
      font: inherit; padding-block: 6px; padding-inline: 12px;
      border-radius: 6px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); color: inherit; cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    button.mode.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff); border-color: transparent;
    }
  `,e([he({attribute:!1})],Li.prototype,"source",void 0),e([he({attribute:!1})],Li.prototype,"rules",void 0),e([he({type:Boolean})],Li.prototype,"canWrite",void 0),e([he({type:Boolean})],Li.prototype,"busy",void 0),e([he()],Li.prototype,"error",void 0),e([he({attribute:!1})],Li.prototype,"landed",void 0),e([he({attribute:!1})],Li.prototype,"failed",void 0),e([he()],Li.prototype,"language",void 0),e([pe()],Li.prototype,"_targetProfile",void 0),e([pe()],Li.prototype,"_targetDay",void 0),e([pe()],Li.prototype,"_mode",void 0),Li=e([ce("shabbat-clone-dialog")],Li);const Fi="not_set_up";let Ui=class extends ae{constructor(){super(...arguments),this._state=null,this._error=null,this._config={},this._selectedProfile=null,this._editing=null,this._creatingDay=null,this._defaultsOpen=!1,this._simulateOpen=!1,this._dialogError=null,this._toggleErrors={},this._busy=!1,this._duplicateSeed=null,this._runNowResult=null,this._cloneSource=null,this._cloneLanded=null,this._cloneFailed=null,this._cloneClearedTargets=new Set,this._unsubscribe=null,this._subscribed=!1,this._generation=0,this._onMaster=e=>{const{enabled:t}=e.detail,i=this._state?.master_entity_id;i&&this._call("switch",t?"turn_on":"turn_off",{entity_id:i})},this._closeDialogs=()=>{this._editing=null,this._creatingDay=null,this._duplicateSeed=null,this._defaultsOpen=!1,this._simulateOpen=!1,this._dialogError=null,this._runNowResult=null,this._cloneSource=null,this._cloneLanded=null,this._cloneFailed=null,this._cloneClearedTargets=new Set},this._onRuleOpen=e=>{this._editing=e.detail.rule,this._creatingDay=null,this._duplicateSeed=null,this._dialogError=null,this._runNowResult=null},this._onRuleToggleEnabled=e=>{const{rule:t}=e.detail;this._toggleRuleEnabled(t)},this._onRuleDelete=async e=>{const{rule:t}=e.detail;try{if(await this._hass.callWS({type:"shabbat_scheduler/rules/delete",rule_id:t.id}),t.id in this._toggleErrors){const e={...this._toggleErrors};delete e[t.id],this._toggleErrors=e}}catch(e){const i=e;this._toggleErrors={...this._toggleErrors,[t.id]:i?.message??String(e)}}},this._onRuleAdd=e=>{this._creatingDay=e.detail.day,this._editing=null,this._duplicateSeed=null,this._dialogError=null,this._runNowResult=null},this._onSave=async e=>{const{form:t,rule:i}=e.detail;(null===i?await this._send({type:"shabbat_scheduler/rules/create",rule:Oe(t,this._profile)}):await this._saveChanges(t,i))&&this._closeDialogs()},this._onDelete=async e=>{const{rule:t}=e.detail;await this._send({type:"shabbat_scheduler/rules/delete",rule_id:t.id})&&this._closeDialogs()},this._onDuplicate=e=>{const{form:t}=e.detail;this._editing=null,this._creatingDay=t.day,this._duplicateSeed=t,this._dialogError=null},this._onDefaultsSave=async e=>{const{defaults:t}=e.detail;await this._send({type:"shabbat_scheduler/defaults/update",defaults:t})&&this._closeDialogs()},this._onLanguageChanged=async e=>{const{language:t}=e.detail;await this._send({type:"shabbat_scheduler/language/update",language:t})},this._onRunNow=async e=>{const{rule:t,simulate:i}=e.detail;try{const e=await this._hass.callWS({type:"shabbat_scheduler/rules/run_now",rule_id:t.id,simulate:i});this._runNowResult={ruleId:t.id,results:e.results,at:(new Date).toISOString()}}catch(e){const t=e;this._dialogError=t?.message??String(e)}},this._onCloneOpen=e=>{this._cloneSource=e.detail,this._cloneLanded=null,this._cloneFailed=null,this._cloneClearedTargets=new Set,this._dialogError=null},this._onCloneConfirm=async e=>{const t=e.detail,i=this._cloneTargetDays(t),n=[],o=[];let r=!1;for(const{day:e,ruleIds:s}of i){if(r){o.push(...s);continue}const i=`${t.targetProfile}:${e}`,a=await this._cloneRules(s,t.targetProfile,e,t.mode,this._cloneClearedTargets.has(i));a.cleared&&this._cloneClearedTargets.add(i),n.push(...a.landed),null!==a.error&&(o.push(...a.failed),r=!0)}this._cloneLanded=n,this._cloneFailed=o,0===o.length&&null===this._dialogError&&(this._cloneSource=null,this._cloneClearedTargets=new Set)}}setConfig(e){this._config=e??{}}getCardSize(){return 3+this._groups.reduce((e,t)=>e+t.rules.length,0)}static getStubConfig(){return{type:"custom:shabbat-scheduler-card"}}set hass(e){const t=this._language,i=this._canWrite;this._hass=e,this._language===t&&this._canWrite===i||this.requestUpdate(),this._ensureSubscribed()}get hass(){return this._hass}_ensureSubscribed(){!this._subscribed&&this._hass&&this.isConnected&&(this._subscribed=!0,this._subscribe())}async _subscribe(){const e=this._generation;try{const t=await this._hass.connection.subscribeMessage(t=>{e===this._generation&&(this._state?.block?.length!==t.block?.length&&(this._selectedProfile=null),this._state=t,this._error=null)},{type:"shabbat_scheduler/subscribe"});if(e!==this._generation||!this.isConnected)return void this._teardown(t);this._unsubscribe=t}catch(t){if(e!==this._generation)return;this._error=function(e){const t=e?.code;if("string"==typeof t)return t===Fi;const i=e?.message;return"string"==typeof i&&i.includes(Fi)}(t)?"not_set_up":"stale",this._subscribed=!1}}async _teardown(e){if(null!==e)try{await e()}catch{}}connectedCallback(){super.connectedCallback(),this._ensureSubscribed()}disconnectedCallback(){super.disconnectedCallback(),this._generation+=1;const e=this._unsubscribe;this._unsubscribe=null,this._subscribed=!1,this._teardown(e)}get _language(){return this._state?.language??this._hass?.locale?.language??"en"}get _canWrite(){return!0===this._hass?.user?.is_admin}get _profile(){return this._selectedProfile??this._state?.block?.length??1}get _groups(){const e=this._state;return null!==e&&Array.isArray(e.rules)?function(e,t){const{block:i}=e,n=t??i?.length??null;if(null===n)return[];const o=ve(e,n),r=String(n);return be(n).map(t=>{const s=e.rules.filter(e=>e.profile===n&&e.day===t).sort((e,t)=>e.time.localeCompare(t.time));let a=null;o||null===i||("erev"===t?a={kind:"candle_lighting",at:i.candle_lighting}:t===r&&(a={kind:"havdalah",at:i.havdalah}));const l=o||null===i?null:i.dates[t]??null;return{day:t,date:l,rules:s,marker:a}}).sort((e,t)=>_e(e.day)-_e(t.day))}(e,this._profile):[]}async _call(e,t,i){try{await this._hass.callService(e,t,i)}catch{this._error="command_failed"}}async _send(e){this._busy=!0,this._dialogError=null;try{return await this._hass.callWS(e),!0}catch(e){const t=e;return this._dialogError=t?.message??String(e),!1}finally{this._busy=!1}}async _toggleRuleEnabled(e){try{if(await this._hass.callWS({type:"shabbat_scheduler/rules/update",rule_id:e.id,changes:{enabled:!e.enabled}}),e.id in this._toggleErrors){const t={...this._toggleErrors};delete t[e.id],this._toggleErrors=t}}catch(t){const i=t;this._toggleErrors={...this._toggleErrors,[e.id]:i?.message??String(t)}}}async _saveChanges(e,t){return this._send({type:"shabbat_scheduler/rules/update",rule_id:t.id,changes:Te(e,t)})}_cloneCreatePayload(e,t,i){return{day:i,profile:t,time:e.time,action:e.action,target:e.target,data:e.data,condition:e.condition,replay:e.replay,name:e.name,icon:e.icon,color:e.color,enabled:e.enabled}}async _cloneRules(e,t,i,n,o=!1){const r=e.map(e=>(this._state?.rules??[]).find(t=>t.id===e)).filter(e=>void 0!==e);let s=o;if("overwrite"===n&&!s){const n=(this._state?.rules??[]).filter(e=>e.profile===t&&e.day===i);for(const t of n){if(!await this._send({type:"shabbat_scheduler/rules/delete",rule_id:t.id}))return{landed:[],failed:e,error:this._dialogError??"Could not clear the target day.",cleared:!1}}s=!0}const a=[];for(const n of e){const o=r.find(e=>e.id===n);if(void 0===o)continue;if(!await this._send({type:"shabbat_scheduler/rules/create",rule:this._cloneCreatePayload(o,t,i)}))return{landed:a,failed:e.slice(a.length),error:this._dialogError,cleared:s};a.push(n)}return{landed:a,failed:[],error:null,cleared:s}}_cloneTargetDays(e){if("day"===e.sourceScope)return[{day:e.targetDay,ruleIds:e.sourceRuleIds}];const t=new Set(["erev"]);for(let i=1;i<=e.targetProfile;i+=1)t.add(String(i));const i=this._state?.rules??[],n=new Map;for(const o of e.sourceRuleIds){const e=i.find(e=>e.id===o);e&&t.has(e.day)&&n.set(e.day,[...n.get(e.day)??[],o])}return[...n.entries()].map(([e,t])=>({day:e,ruleIds:t}))}render(){const e=this._error;if("not_set_up"===e)return B`
        <ha-card>
          <div class="message">${fe(this._language,"not_set_up")}</div>
        </ha-card>
      `;if(null===this._state)return B`
        <ha-card>
          <div class="message">
            ${null===e?"…":fe(this._language,e)}
          </div>
        </ha-card>
      `;const t=this._groups,i=t.flatMap(e=>e.rules.map(e=>e.id));return B`
      <ha-card
        @rule-open=${this._onRuleOpen}
        @rule-toggle-enabled=${this._onRuleToggleEnabled}
        @rule-delete=${this._onRuleDelete}
        @simulate-open=${()=>{this._simulateOpen=!0}}
        @clone-open=${this._onCloneOpen}
      >
        ${this._config.title?B`<div class="title">${this._config.title}</div>`:q}
        ${null!==e?B`<div class="message notice">${fe(this._language,e)}</div>`:q}
        <shabbat-block-header
          .hass=${this._hass}
          .block=${this._state.block}
          .enabled=${this._state.enabled}
          .canWrite=${this._canWrite}
          .masterEntityId=${this._state.master_entity_id}
          .selectedProfile=${this._profile}
          .language=${this._language}
          @shabbat-master-toggle=${this._onMaster}
          @profile-selected=${e=>{this._selectedProfile=e.detail.profile}}
          @defaults-open=${()=>{this._defaultsOpen=!0}}
        ></shabbat-block-header>
        ${ve(this._state,this._profile)?B`<div class="preview">${fe(this._language,"preview_banner")}</div>`:q}
        <shabbat-warnings
          .warnings=${this._state.warnings}
          .displayedRuleIds=${i}
          .language=${this._language}
        ></shabbat-warnings>
        ${t.map(e=>B`
            <shabbat-day-group
              .hass=${this._hass}
              .group=${e}
              .profile=${this._profile}
              .defaults=${this._state.defaults}
              .warnings=${this._state.warnings}
              .language=${this._language}
              .canWrite=${this._canWrite}
              .toggleErrors=${this._toggleErrors}
              @rule-add=${this._onRuleAdd}
            ></shabbat-day-group>
          `)}
        ${null!==this._editing||null!==this._creatingDay?B`<shabbat-rule-dialog
              .hass=${this._hass}
              .rule=${this._editing}
              .seed=${this._duplicateSeed}
              .day=${this._creatingDay??this._editing?.day??"erev"}
              .profile=${this._profile}
              .defaults=${this._state.defaults}
              .canWrite=${this._canWrite}
              .busy=${this._busy}
              .error=${this._dialogError}
              .language=${this._language}
              .runNowResult=${this._runNowResult}
              @dialog-save=${this._onSave}
              @dialog-delete=${this._onDelete}
              @dialog-duplicate=${this._onDuplicate}
              @dialog-run-now=${this._onRunNow}
              @dialog-close=${this._closeDialogs}
            ></shabbat-rule-dialog>`:q}
        ${this._defaultsOpen?B`<shabbat-defaults-dialog
              .hass=${this._hass}
              .defaults=${this._state.defaults}
              .canWrite=${this._canWrite}
              .busy=${this._busy}
              .error=${this._dialogError}
              .language=${this._language}
              .languageOverride=${this._state.language}
              @dialog-save=${this._onDefaultsSave}
              @language-changed=${this._onLanguageChanged}
              @dialog-close=${this._closeDialogs}
            ></shabbat-defaults-dialog>`:q}
        ${this._simulateOpen?B`<shabbat-simulate-dialog
              .hass=${this._hass}
              .language=${this._language}
              .canWrite=${this._canWrite}
              @dialog-close=${()=>{this._simulateOpen=!1}}
            ></shabbat-simulate-dialog>`:q}
        ${null!==this._cloneSource?B`<shabbat-clone-dialog
              .source=${this._cloneSource}
              .rules=${this._state.rules}
              .canWrite=${this._canWrite}
              .busy=${this._busy}
              .error=${this._dialogError}
              .landed=${this._cloneLanded}
              .failed=${this._cloneFailed}
              .language=${this._language}
              @dialog-clone-confirm=${this._onCloneConfirm}
              @dialog-close=${()=>{this._cloneSource=null,this._cloneClearedTargets=new Set}}
            ></shabbat-clone-dialog>`:q}
      </ha-card>
    `}};Ui.styles=s`
    ha-card { padding: 16px; }
    .title { font-size: 1.1em; font-weight: 600; margin-block-end: 8px; }
    .message { color: var(--secondary-text-color, #666); padding-block: 8px; }
    .notice { color: var(--warning-color, #d9822b); }
    .preview {
      background: var(--secondary-background-color, #f4f4f4);
      border-inline-start: 3px solid var(--primary-color, #03a9f4);
      padding-block: 8px;
      padding-inline: 12px;
      margin-block: 8px;
      font-size: 0.9em;
    }
  `,e([pe()],Ui.prototype,"_state",void 0),e([pe()],Ui.prototype,"_error",void 0),e([he({attribute:!1})],Ui.prototype,"_config",void 0),e([pe()],Ui.prototype,"_selectedProfile",void 0),e([pe()],Ui.prototype,"_editing",void 0),e([pe()],Ui.prototype,"_creatingDay",void 0),e([pe()],Ui.prototype,"_defaultsOpen",void 0),e([pe()],Ui.prototype,"_simulateOpen",void 0),e([pe()],Ui.prototype,"_dialogError",void 0),e([pe()],Ui.prototype,"_toggleErrors",void 0),e([pe()],Ui.prototype,"_busy",void 0),e([pe()],Ui.prototype,"_duplicateSeed",void 0),e([pe()],Ui.prototype,"_runNowResult",void 0),e([pe()],Ui.prototype,"_cloneSource",void 0),e([pe()],Ui.prototype,"_cloneLanded",void 0),e([pe()],Ui.prototype,"_cloneFailed",void 0),Ui=e([ce("shabbat-scheduler-card")],Ui),window.customCards=window.customCards??[],window.customCards.push({type:"shabbat-scheduler-card",name:"Shabbat Scheduler",description:"The coming Shabbat or Chag as a timeline."}),console.info("shabbat-scheduler-card 0.13.0");export{Ui as ShabbatSchedulerCard};
