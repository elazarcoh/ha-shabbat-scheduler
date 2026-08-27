function e(e,t,i,n){var r,o=arguments.length,s=o<3?t:null===n?n=Object.getOwnPropertyDescriptor(t,i):n;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)s=Reflect.decorate(e,t,i,n);else for(var a=e.length-1;a>=0;a--)(r=e[a])&&(s=(o<3?r(s):o>3?r(t,i,s):r(t,i))||s);return o>3&&s&&Object.defineProperty(t,i,s),s}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,n=Symbol(),r=new WeakMap;let o=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==n)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=r.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&r.set(t,e))}return e}toString(){return this.cssText}};const s=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,n)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[n+1],e[0]);return new o(i,e,n)},a=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new o("string"==typeof e?e:e+"",void 0,n))(t)})(e):e,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:u,getOwnPropertySymbols:h,getPrototypeOf:p}=Object,f=globalThis,g=f.trustedTypes,_=g?g.emptyScript:"",b=f.reactiveElementPolyfillSupport,v=(e,t)=>e,m={toAttribute(e,t){switch(t){case Boolean:e=e?_:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},y=(e,t)=>!l(e,t),$={attribute:!0,type:String,converter:m,reflect:!1,useDefault:!1,hasChanged:y};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),f.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=$){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),n=this.getPropertyDescriptor(e,i,t);void 0!==n&&c(this.prototype,e,n)}}static getPropertyDescriptor(e,t,i){const{get:n,set:r}=d(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:n,set(t){const o=n?.call(this);r?.call(this,t),this.requestUpdate(e,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??$}static _$Ei(){if(this.hasOwnProperty(v("elementProperties")))return;const e=p(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(v("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(v("properties"))){const e=this.properties,t=[...u(e),...h(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(a(e))}else void 0!==e&&t.push(a(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,n)=>{if(i)e.adoptedStyleSheets=n.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of n){const n=document.createElement("style"),r=t.litNonce;void 0!==r&&n.setAttribute("nonce",r),n.textContent=i.cssText,e.appendChild(n)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),n=this.constructor._$Eu(e,i);if(void 0!==n&&!0===i.reflect){const r=(void 0!==i.converter?.toAttribute?i.converter:m).toAttribute(t,i.type);this._$Em=e,null==r?this.removeAttribute(n):this.setAttribute(n,r),this._$Em=null}}_$AK(e,t){const i=this.constructor,n=i._$Eh.get(e);if(void 0!==n&&this._$Em!==n){const e=i.getPropertyOptions(n),r="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:m;this._$Em=n;const o=r.fromAttribute(t,e.type);this[n]=o??this._$Ej?.get(n)??o,this._$Em=null}}requestUpdate(e,t,i,n=!1,r){if(void 0!==e){const o=this.constructor;if(!1===n&&(r=this[e]),i??=o.getPropertyOptions(e),!((i.hasChanged??y)(r,t)||i.useDefault&&i.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:n,wrapped:r},o){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),!0!==r||void 0!==o)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===n&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,n=this[t];!0!==e||this._$AL.has(t)||void 0===n||this.C(t,void 0,i,n)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[v("elementProperties")]=new Map,w[v("finalized")]=new Map,b?.({ReactiveElement:w}),(f.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x=globalThis,k=e=>e,A=x.trustedTypes,C=A?A.createPolicy("lit-html",{createHTML:e=>e}):void 0,S="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,O="?"+E,I=`<${O}>`,N=document,T=()=>N.createComment(""),j=e=>null===e||"object"!=typeof e&&"function"!=typeof e,R=Array.isArray,P="[ \t\n\f\r]",M=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,D=/-->/g,z=/>/g,W=RegExp(`>|${P}(?:([^\\s"'>=/]+)(${P}*=${P}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),L=/'/g,U=/"/g,F=/^(?:script|style|textarea|title)$/i,B=(e=>(t,...i)=>({_$litType$:e,strings:t,values:i}))(1),H=Symbol.for("lit-noChange"),q=Symbol.for("lit-nothing"),Y=new WeakMap,V=N.createTreeWalker(N,129);function K(e,t){if(!R(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==C?C.createHTML(t):t}const G=(e,t)=>{const i=e.length-1,n=[];let r,o=2===t?"<svg>":3===t?"<math>":"",s=M;for(let t=0;t<i;t++){const i=e[t];let a,l,c=-1,d=0;for(;d<i.length&&(s.lastIndex=d,l=s.exec(i),null!==l);)d=s.lastIndex,s===M?"!--"===l[1]?s=D:void 0!==l[1]?s=z:void 0!==l[2]?(F.test(l[2])&&(r=RegExp("</"+l[2],"g")),s=W):void 0!==l[3]&&(s=W):s===W?">"===l[0]?(s=r??M,c=-1):void 0===l[1]?c=-2:(c=s.lastIndex-l[2].length,a=l[1],s=void 0===l[3]?W:'"'===l[3]?U:L):s===U||s===L?s=W:s===D||s===z?s=M:(s=W,r=void 0);const u=s===W&&e[t+1].startsWith("/>")?" ":"";o+=s===M?i+I:c>=0?(n.push(a),i.slice(0,c)+S+i.slice(c)+E+u):i+E+(-2===c?t:u)}return[K(e,o+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),n]};class J{constructor({strings:e,_$litType$:t},i){let n;this.parts=[];let r=0,o=0;const s=e.length-1,a=this.parts,[l,c]=G(e,t);if(this.el=J.createElement(l,i),V.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(n=V.nextNode())&&a.length<s;){if(1===n.nodeType){if(n.hasAttributes())for(const e of n.getAttributeNames())if(e.endsWith(S)){const t=c[o++],i=n.getAttribute(e).split(E),s=/([.?@])?(.*)/.exec(t);a.push({type:1,index:r,name:s[2],strings:i,ctor:"."===s[1]?te:"?"===s[1]?ie:"@"===s[1]?ne:ee}),n.removeAttribute(e)}else e.startsWith(E)&&(a.push({type:6,index:r}),n.removeAttribute(e));if(F.test(n.tagName)){const e=n.textContent.split(E),t=e.length-1;if(t>0){n.textContent=A?A.emptyScript:"";for(let i=0;i<t;i++)n.append(e[i],T()),V.nextNode(),a.push({type:2,index:++r});n.append(e[t],T())}}}else if(8===n.nodeType)if(n.data===O)a.push({type:2,index:r});else{let e=-1;for(;-1!==(e=n.data.indexOf(E,e+1));)a.push({type:7,index:r}),e+=E.length-1}r++}}static createElement(e,t){const i=N.createElement("template");return i.innerHTML=e,i}}function Z(e,t,i=e,n){if(t===H)return t;let r=void 0!==n?i._$Co?.[n]:i._$Cl;const o=j(t)?void 0:t._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),void 0===o?r=void 0:(r=new o(e),r._$AT(e,i,n)),void 0!==n?(i._$Co??=[])[n]=r:i._$Cl=r),void 0!==r&&(t=Z(e,r._$AS(e,t.values),r,n)),t}class Q{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,n=(e?.creationScope??N).importNode(t,!0);V.currentNode=n;let r=V.nextNode(),o=0,s=0,a=i[0];for(;void 0!==a;){if(o===a.index){let t;2===a.type?t=new X(r,r.nextSibling,this,e):1===a.type?t=new a.ctor(r,a.name,a.strings,this,e):6===a.type&&(t=new re(r,this,e)),this._$AV.push(t),a=i[++s]}o!==a?.index&&(r=V.nextNode(),o++)}return V.currentNode=N,n}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class X{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,n){this.type=2,this._$AH=q,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=Z(this,e,t),j(e)?e===q||null==e||""===e?(this._$AH!==q&&this._$AR(),this._$AH=q):e!==this._$AH&&e!==H&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>R(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==q&&j(this._$AH)?this._$AA.nextSibling.data=e:this.T(N.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,n="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=J.createElement(K(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===n)this._$AH.p(t);else{const e=new Q(n,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=Y.get(e.strings);return void 0===t&&Y.set(e.strings,t=new J(e)),t}k(e){R(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,n=0;for(const r of e)n===t.length?t.push(i=new X(this.O(T()),this.O(T()),this,this.options)):i=t[n],i._$AI(r),n++;n<t.length&&(this._$AR(i&&i._$AB.nextSibling,n),t.length=n)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ee{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,n,r){this.type=1,this._$AH=q,this._$AN=void 0,this.element=e,this.name=t,this._$AM=n,this.options=r,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=q}_$AI(e,t=this,i,n){const r=this.strings;let o=!1;if(void 0===r)e=Z(this,e,t,0),o=!j(e)||e!==this._$AH&&e!==H,o&&(this._$AH=e);else{const n=e;let s,a;for(e=r[0],s=0;s<r.length-1;s++)a=Z(this,n[i+s],t,s),a===H&&(a=this._$AH[s]),o||=!j(a)||a!==this._$AH[s],a===q?e=q:e!==q&&(e+=(a??"")+r[s+1]),this._$AH[s]=a}o&&!n&&this.j(e)}j(e){e===q?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class te extends ee{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===q?void 0:e}}class ie extends ee{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==q)}}class ne extends ee{constructor(e,t,i,n,r){super(e,t,i,n,r),this.type=5}_$AI(e,t=this){if((e=Z(this,e,t,0)??q)===H)return;const i=this._$AH,n=e===q&&i!==q||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,r=e!==q&&(i===q||n);n&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class re{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){Z(this,e)}}const oe=x.litHtmlPolyfillSupport;oe?.(J,X),(x.litHtmlVersions??=[]).push("3.3.3");const se=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */let ae=class extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const n=i?.renderBefore??t;let r=n._$litPart$;if(void 0===r){const e=i?.renderBefore??null;n._$litPart$=r=new X(t.insertBefore(T(),e),e,void 0,i??{})}return r._$AI(e),r})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return H}};ae._$litElement$=!0,ae.finalized=!0,se.litElementHydrateSupport?.({LitElement:ae});const le=se.litElementPolyfillSupport;le?.({LitElement:ae}),(se.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ce=e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},de={attribute:!0,type:String,converter:m,reflect:!1,hasChanged:y},ue=(e=de,t,i)=>{const{kind:n,metadata:r}=i;let o=globalThis.litPropertyMetadata.get(r);if(void 0===o&&globalThis.litPropertyMetadata.set(r,o=new Map),"setter"===n&&((e=Object.create(e)).wrapped=!0),o.set(i.name,e),"accessor"===n){const{name:n}=i;return{set(i){const r=t.get.call(this);t.set.call(this,i),this.requestUpdate(n,r,e,!0,i)},init(t){return void 0!==t&&this.C(n,void 0,e,t),t}}}if("setter"===n){const{name:n}=i;return function(i){const r=this[n];t.call(this,i),this.requestUpdate(n,r,e,!0,i)}}throw Error("Unsupported decorator location: "+n)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function he(e){return(t,i)=>"object"==typeof i?ue(e,t,i):((e,t,i)=>{const n=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),n?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pe(e){return he({...e,state:!0,attribute:!1})}const fe={en:{erev:"Erev",day:"Day",candle_lighting:"Candle lighting",havdalah:"Havdalah",master:"Shabbat Scheduler",no_block:"No upcoming Shabbat could be derived from the Jewish Calendar sensors.",not_set_up:"Shabbat Scheduler is not configured.",stale:"Connection lost — showing the last known state.",command_failed:"That did not go through. Nothing was changed.",no_rules:"No rules for this block.",disabled_rule:"disabled",conflict_prefix:"Conflict",edit_rule:"Edit rule",add_rule:"Add rule",time:"Time",name:"Name",enabled:"Enabled",advanced:"Advanced",icon:"Icon",colour:"Colour",save:"Save",cancel:"Cancel",delete_rule:"Delete",duplicate:"Duplicate",read_only:"You do not have permission to change the schedule.",will_conflict:"This overlaps another rule. You can still save it — nothing is resolved for you.",defaults_title:"Shared defaults",defaults_help:"Rules inherit these unless they set their own.",target:"Target",data:"Data",migration_error:"This rule could not be converted from the old format and will not fire:",preview_banner:"Preview — not the coming Shabbat. Dates are not shown because this block is not scheduled.",inherits_target_from_defaults:"Inherited from the shared defaults:",target_none:"No target — this rule will not reach anything.",replay_after_restart:"Replay after a restart",replay_within_label:"Only if less than",replay_help:"Off by default: after a restart, nothing that already passed is re-run.",conditions:"Conditions",conditions_help:"All conditions must pass, or the rule does not run and says why.",add_condition:"Add condition",remove_condition:"Remove",condition_unparseable:"Not valid YAML — this condition is not being saved.",condition_not_a_mapping:"A condition must be a mapping, like `condition: state`.",outcome_called:"Fired",outcome_would_call:"Would have fired [dry run]",outcome_failed:"Did not run — failed",outcome_blocked:"Did not run — blocked",outcome_skipped_stale:"Did not run — skipped as stale",outcome_skipped_no_replay:"Did not run — was due after a restart, replay is off",outcome_unknown:"Finished with no reported outcome",outcome_no_such_entity:"no such entity: ",outcome_reached_nothing:"reached no entity that exists",run_now_button:"Run now",run_now_simulate:"Simulate",run_now_real:"Run for real",simulate_title:"Test your schedule",simulate_profile:"Block length",simulate_day:"Day",simulate_force_conditions:"Force conditions to pass",simulate_this_day:"Simulate this day",simulate_run_for_real:"Run this day for real",clone_day_prefix:"Clone day",clone_profile_prefix:"Clone the",clone_profile_suffix:"-day profile",clone_target_profile:"Target block length",clone_target_day:"Target day",clone_extend:"Extend",clone_overwrite:"Overwrite",clone_target_has_rules:"The target has existing rule(s):",clone_confirm:"Clone",clone_landed:"Cloned",clone_failed:"Not cloned",clone_none:"none"},he:{erev:"ערב",day:"יום",candle_lighting:"הדלקת נרות",havdalah:"הבדלה",master:"שעון שבת",no_block:"לא ניתן לגזור שבת קרובה מחיישני לוח השנה העברי.",not_set_up:"שעון שבת אינו מוגדר.",stale:"החיבור אבד — מוצג המצב האחרון הידוע.",command_failed:"הפעולה לא בוצעה. שום דבר לא השתנה.",no_rules:"אין כללים לבלוק הזה.",disabled_rule:"מושבת",conflict_prefix:"התנגשות",edit_rule:"עריכת כלל",add_rule:"הוספת כלל",time:"שעה",name:"שם",enabled:"מופעל",advanced:"מתקדם",icon:"סמל",colour:"צבע",save:"שמירה",cancel:"ביטול",delete_rule:"מחיקה",duplicate:"שכפול",read_only:"אין לך הרשאה לשנות את הלוח.",will_conflict:"הכלל חופף לכלל אחר. אפשר לשמור בכל זאת — שום דבר לא ייפתר עבורך.",defaults_title:"ברירות מחדל משותפות",defaults_help:"כללים יורשים אותן אלא אם הגדירו משלהם.",target:"יעד",data:"נתונים",migration_error:"לא ניתן להמיר את הכלל הזה מהפורמט הישן והוא לא יופעל:",preview_banner:"תצוגה מקדימה — לא השבת הקרובה. התאריכים אינם מוצגים כי הבלוק הזה אינו מתוכנן.",inherits_target_from_defaults:"נורש מברירת המחדל המשותפת:",target_none:"ללא יעד — הכלל לא יפעל על שום דבר.",replay_after_restart:"הפעלה חוזרת לאחר אתחול",replay_within_label:"רק אם עברו פחות מ־",replay_help:"כברירת מחדל כבוי: לאחר אתחול, מה שכבר עבר לא יופעל שוב.",conditions:"תנאים",conditions_help:"כל התנאים חייבים להתקיים, אחרת הכלל לא ירוץ ויציין זאת.",add_condition:"הוספת תנאי",remove_condition:"הסרה",condition_unparseable:"YAML לא תקין — התנאי הזה לא נשמר.",condition_not_a_mapping:"תנאי חייב להיות מפה, כמו `condition: state`.",outcome_called:"הופעל",outcome_would_call:"היה מופעל [הרצה יבשה]",outcome_failed:"לא רץ — נכשל",outcome_blocked:"לא רץ — נחסם",outcome_skipped_stale:"לא רץ — דולג כמיושן",outcome_skipped_no_replay:"לא רץ — היה אמור לרוץ לאחר אתחול, הפעלה חוזרת כבויה",outcome_unknown:"הסתיים ללא תוצאה מדווחת",outcome_no_such_entity:"אין ישות כזו: ",outcome_reached_nothing:"לא הגיע לאף ישות קיימת",run_now_button:"הרצה עכשיו",run_now_simulate:"סימולציה",run_now_real:"הרצה אמיתית",simulate_title:"בדיקת הלוח",simulate_profile:"אורך הבלוק",simulate_day:"יום",simulate_force_conditions:"לעקוף תנאים",simulate_this_day:"סימולציה ליום זה",simulate_run_for_real:"הרצה אמיתית ליום זה",clone_day_prefix:"שכפול יום",clone_profile_prefix:"שכפול פרופיל בן",clone_profile_suffix:"ימים",clone_target_profile:"אורך היעד",clone_target_day:"יום היעד",clone_extend:"הוספה",clone_overwrite:"החלפה",clone_target_has_rules:"ליעד כבר יש כללים:",clone_confirm:"שכפול",clone_landed:"שוכפלו",clone_failed:"לא שוכפלו",clone_none:"ללא"}};function ge(e,t){return("he"===e?fe.he:fe.en)[t]}function _e(e){return"erev"===e?-1:Number(e)}function be(e){const t=["erev"];for(let i=1;i<=e;i+=1)t.push(String(i));return t}function ve(e){return function(e){return be(e.length)}(e).map(t=>e.dates[t]).filter(e=>void 0!==e)}function me(e,t){return null===e.block||e.block.length!==t}function ye(e){const t=[];for(const i of Object.values(e))Array.isArray(i)?t.push(...i.map(String)):null!=i&&t.push(String(i));return t.join(", ")}function $e(e,t){if("conflict"===e.kind&&void 0!==e.targets&&e.targets.length>0&&void 0!==e.time){const i=[ge(t,"conflict_prefix"),e.targets.join(", ")];return void 0!==e.day&&i.push(function(e,t){return"erev"===e?ge(t,"erev"):`${ge(t,"day")} ${e}`}(e.day,t)),i.push(e.time),i.join(" · ")}return e.message??""}const we={called:"outcome_called",would_call:"outcome_would_call",failed:"outcome_failed",blocked:"outcome_blocked",skipped_stale:"outcome_skipped_stale",skipped_no_replay:"outcome_skipped_no_replay"};function xe(e,t){let i=ge(t,we[e.outcome]??"outcome_unknown");e.detail&&(i=`${i}: ${e.detail}`);const n=e.unknown_targets??[];return n.length>0&&!i.includes("no such entity: ")&&(i=`${i} — ${ge(t,"outcome_no_such_entity")}${n.join(", ")}`),!0===e.no_live_targets&&(i=`${i} — ${ge(t,"outcome_reached_nothing")}`),i}const ke=["failed","blocked","skipped_stale","skipped_no_replay","would_call","called"];function Ae(e,t){if(0===e.length)return{outcome:"unknown",at:t,detail:null};const i=new Set(e.map(e=>String(e.outcome??""))),n=ke.find(e=>i.has(e))??"unknown",r=e.find(e=>e.outcome===n&&(e.error||e.reason)),o=Array.from(new Set(e.flatMap(e=>e.unknown_targets??[])));return{outcome:n,at:t,detail:r?.error??r?.reason??null,unknown_targets:o.length?o:void 0,no_live_targets:e.some(e=>!0===e.no_live_targets)||void 0}}const Ce=["day","time","action","target","data","condition","replay","name","icon","color","enabled"];function Se(e,t){return{...e,profile:t}}function Ee(e,t){const i={};for(const n of Ce){const r=e[n],o=t[n];JSON.stringify(r)!==JSON.stringify(o)&&(i[n]=r)}return i}let Oe=class extends ae{constructor(){super(...arguments),this.hass=null,this.block=null,this.enabled=!1,this.canWrite=!1,this.masterEntityId=null,this.language="en",this.selectedProfile=1,this._onMasterChanged=e=>{this.dispatchEvent(new CustomEvent("shabbat-master-toggle",{detail:{enabled:Boolean(e.detail?.value)}}))}}_dates(){return null===this.block?"":ve(this.block).join(" → ")}render(){return B`
      <div class="header">
        <div class="label">
          ${null===this.block?B`<span class="none">${ge(this.language,"no_block")}</span>`:B`
                <span>${ge(this.language,"day")} ×${this.block.length}</span>
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
                aria-label=${ge(this.language,"clone_profile_prefix")}
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
              aria-label=${ge(this.language,"simulate_title")}
              @click=${()=>this.dispatchEvent(new CustomEvent("simulate-open",{bubbles:!0,composed:!0}))}
            >
              ▶
            </button>`:q}
        <div class="master-wrap">
          <span class="master-label">${ge(this.language,"master")}</span>
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
    `}};Oe.styles=s`
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
  `,e([he({attribute:!1})],Oe.prototype,"hass",void 0),e([he({attribute:!1})],Oe.prototype,"block",void 0),e([he({type:Boolean})],Oe.prototype,"enabled",void 0),e([he({type:Boolean})],Oe.prototype,"canWrite",void 0),e([he()],Oe.prototype,"masterEntityId",void 0),e([he()],Oe.prototype,"language",void 0),e([he({type:Number})],Oe.prototype,"selectedProfile",void 0),Oe=e([ce("shabbat-block-header")],Oe);let Ie=class extends ae{constructor(){super(...arguments),this.hass=null,this.defaults={},this.warnings=[],this.canWrite=!1,this.toggleError=null,this.language="en"}_open(){this.dispatchEvent(new CustomEvent("rule-open",{detail:{rule:this.rule},bubbles:!0,composed:!0}))}render(){const e=(t=this.rule.id,this.warnings.filter(e=>e.rule_ids?.includes(t)));var t;const i=this.rule.name,n=this.rule.last_outcome??null,r=null===n?"":function(e,t){const i=new Date(e);return Number.isNaN(i.getTime())?"":i.toLocaleString("he"===t?"he-IL":"en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}(n.at,this.language);return B`
      <div
        class="row ${this.rule.enabled?"":"disabled"}"
        tabindex="0"
        role="button"
        @click=${()=>this._open()}
        @keydown=${e=>{"Enter"!==e.key&&" "!==e.key||(e.preventDefault(),this._open())}}
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
        <span class="dot" style="background:${o=this.rule,o.color??"var(--secondary-text-color, #888)"}"></span>
        <span class="time">${this.rule.time.slice(0,5)}</span>
        <div class="body">
          ${i?B`<div class="title">${i}</div>`:q}
          <div class="brief">${function(e,t){const i=Object.keys(e.target).length?e.target:t.target??{},n={...t.data??{},...e.data},r=[e.action,ye(i)];for(const e of Object.values(n))null!=e&&r.push(String(e));return r.filter(e=>""!==e).join(" · ")}(this.rule,this.defaults)}</div>
          ${null!==this.toggleError?B`<div class="row-error">${this.toggleError}</div>`:q}
          ${null!==n?B`<div class="last-outcome ${function(e){return"failed"===e.outcome||"blocked"===e.outcome||"skipped_stale"===e.outcome||(e.unknown_targets??[]).length>0||!0===e.no_live_targets||!(e.outcome in we)}(n)?"bad":""}">
                <span>${xe(n,this.language)}</span>
                ${r?B`<span class="last-outcome-at">${r}</span>`:q}
              </div>`:q}
          ${e.length?B`<div class="conflict-detail">
                ${e.map(e=>B`<div>${$e(e,this.language)}</div>`)}
              </div>`:q}
        </div>
        ${this.rule.enabled?q:B`<span class="tag">${ge(this.language,"disabled_rule")}</span>`}
        ${e.length?B`<span
              class="conflict"
              role="img"
              aria-label=${e.map(e=>$e(e,this.language)).join("; ")}
              title=${$e(e[0],this.language)}
              >⚠</span
            >`:q}
      </div>
    `;var o}};Ie.styles=s`
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
    @media (max-width: 599px) {
      .row { flex-wrap: wrap; row-gap: 4px; }
      .body { display: contents; }
      .brief, .last-outcome, .conflict-detail { flex-basis: 100%; }
    }
  `,e([he({attribute:!1})],Ie.prototype,"hass",void 0),e([he({attribute:!1})],Ie.prototype,"rule",void 0),e([he({attribute:!1})],Ie.prototype,"defaults",void 0),e([he({attribute:!1})],Ie.prototype,"warnings",void 0),e([he({type:Boolean})],Ie.prototype,"canWrite",void 0),e([he()],Ie.prototype,"toggleError",void 0),e([he()],Ie.prototype,"language",void 0),Ie=e([ce("shabbat-rule-row")],Ie);let Ne=class extends ae{constructor(){super(...arguments),this.hass=null,this.defaults={},this.warnings=[],this.language="en",this.canWrite=!1,this.profile=1,this.toggleErrors={}}label(){const{day:e}=this.group;return"erev"===e?ge(this.language,"erev"):`${ge(this.language,"day")} ${e}`}render(){const{marker:e,rules:t}=this.group;return B`
      <div class="day-group">
        <div class="heading">
          <span>${this.label()}</span>
          <span class="date">${this.group.date??""}</span>
          ${this.canWrite?B`<button
                class="clone-menu"
                aria-label=${ge(this.language,"clone_day_prefix")}
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
              `):B`<div class="empty">${ge(this.language,"no_rules")}</div>`}
        ${this.canWrite?B`<button
              class="add"
              @click=${()=>this.dispatchEvent(new CustomEvent("rule-add",{detail:{day:this.group.day}}))}
            >
              + ${ge(this.language,"add_rule")}
            </button>`:q}
        ${e?B`
              <div class="marker">
                <span>${"havdalah"===e.kind?"✨":"🕯️"}</span>
                <span>${ge(this.language,e.kind)}</span>
                <span>${function(e){const t=/T(\d{2}:\d{2})/.exec(e);return t?t[1]:e}(e.at)}</span>
              </div>
            `:q}
      </div>
    `}};Ne.styles=s`
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
  `,e([he({attribute:!1})],Ne.prototype,"hass",void 0),e([he({attribute:!1})],Ne.prototype,"group",void 0),e([he({attribute:!1})],Ne.prototype,"defaults",void 0),e([he({attribute:!1})],Ne.prototype,"warnings",void 0),e([he()],Ne.prototype,"language",void 0),e([he({type:Boolean})],Ne.prototype,"canWrite",void 0),e([he({type:Number})],Ne.prototype,"profile",void 0),e([he({attribute:!1})],Ne.prototype,"toggleErrors",void 0),Ne=e([ce("shabbat-day-group")],Ne);let Te=class extends ae{constructor(){super(...arguments),this.warnings=[],this.displayedRuleIds=[],this.language="en"}render(){const e=function(e,t){const i=new Set(t);return e.filter(e=>!e.rule_ids?.some(e=>i.has(e)))}(this.warnings,this.displayedRuleIds);return e.length?B`
      <div class="banner">
        ${e.map(e=>B`<span>${$e(e,this.language)}</span>`)}
      </div>
    `:q}};
/*! js-yaml 4.1.0 https://github.com/nodeca/js-yaml @license MIT */
function je(e){return null==e}Te.styles=s`
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
  `,e([he({attribute:!1})],Te.prototype,"warnings",void 0),e([he({attribute:!1})],Te.prototype,"displayedRuleIds",void 0),e([he()],Te.prototype,"language",void 0),Te=e([ce("shabbat-warnings")],Te);var Re={isNothing:je,isObject:function(e){return"object"==typeof e&&null!==e},toArray:function(e){return Array.isArray(e)?e:je(e)?[]:[e]},repeat:function(e,t){var i,n="";for(i=0;i<t;i+=1)n+=e;return n},isNegativeZero:function(e){return 0===e&&Number.NEGATIVE_INFINITY===1/e},extend:function(e,t){var i,n,r,o;if(t)for(i=0,n=(o=Object.keys(t)).length;i<n;i+=1)e[r=o[i]]=t[r];return e}};function Pe(e,t){var i="",n=e.reason||"(unknown reason)";return e.mark?(e.mark.name&&(i+='in "'+e.mark.name+'" '),i+="("+(e.mark.line+1)+":"+(e.mark.column+1)+")",!t&&e.mark.snippet&&(i+="\n\n"+e.mark.snippet),n+" "+i):n}function Me(e,t){Error.call(this),this.name="YAMLException",this.reason=e,this.mark=t,this.message=Pe(this,!1),Error.captureStackTrace?Error.captureStackTrace(this,this.constructor):this.stack=(new Error).stack||""}Me.prototype=Object.create(Error.prototype),Me.prototype.constructor=Me,Me.prototype.toString=function(e){return this.name+": "+Pe(this,e)};var De=Me;function ze(e,t,i,n,r){var o="",s="",a=Math.floor(r/2)-1;return n-t>a&&(t=n-a+(o=" ... ").length),i-n>a&&(i=n+a-(s=" ...").length),{str:o+e.slice(t,i).replace(/\t/g,"→")+s,pos:n-t+o.length}}function We(e,t){return Re.repeat(" ",t-e.length)+e}var Le=function(e,t){if(t=Object.create(t||null),!e.buffer)return null;t.maxLength||(t.maxLength=79),"number"!=typeof t.indent&&(t.indent=1),"number"!=typeof t.linesBefore&&(t.linesBefore=3),"number"!=typeof t.linesAfter&&(t.linesAfter=2);for(var i,n=/\r?\n|\r|\0/g,r=[0],o=[],s=-1;i=n.exec(e.buffer);)o.push(i.index),r.push(i.index+i[0].length),e.position<=i.index&&s<0&&(s=r.length-2);s<0&&(s=r.length-1);var a,l,c="",d=Math.min(e.line+t.linesAfter,o.length).toString().length,u=t.maxLength-(t.indent+d+3);for(a=1;a<=t.linesBefore&&!(s-a<0);a++)l=ze(e.buffer,r[s-a],o[s-a],e.position-(r[s]-r[s-a]),u),c=Re.repeat(" ",t.indent)+We((e.line-a+1).toString(),d)+" | "+l.str+"\n"+c;for(l=ze(e.buffer,r[s],o[s],e.position,u),c+=Re.repeat(" ",t.indent)+We((e.line+1).toString(),d)+" | "+l.str+"\n",c+=Re.repeat("-",t.indent+d+3+l.pos)+"^\n",a=1;a<=t.linesAfter&&!(s+a>=o.length);a++)l=ze(e.buffer,r[s+a],o[s+a],e.position-(r[s]-r[s+a]),u),c+=Re.repeat(" ",t.indent)+We((e.line+a+1).toString(),d)+" | "+l.str+"\n";return c.replace(/\n$/,"")},Ue=["kind","multi","resolve","construct","instanceOf","predicate","represent","representName","defaultStyle","styleAliases"],Fe=["scalar","sequence","mapping"];var Be=function(e,t){if(t=t||{},Object.keys(t).forEach(function(t){if(-1===Ue.indexOf(t))throw new De('Unknown option "'+t+'" is met in definition of "'+e+'" YAML type.')}),this.options=t,this.tag=e,this.kind=t.kind||null,this.resolve=t.resolve||function(){return!0},this.construct=t.construct||function(e){return e},this.instanceOf=t.instanceOf||null,this.predicate=t.predicate||null,this.represent=t.represent||null,this.representName=t.representName||null,this.defaultStyle=t.defaultStyle||null,this.multi=t.multi||!1,this.styleAliases=function(e){var t={};return null!==e&&Object.keys(e).forEach(function(i){e[i].forEach(function(e){t[String(e)]=i})}),t}(t.styleAliases||null),-1===Fe.indexOf(this.kind))throw new De('Unknown kind "'+this.kind+'" is specified for "'+e+'" YAML type.')};function He(e,t){var i=[];return e[t].forEach(function(e){var t=i.length;i.forEach(function(i,n){i.tag===e.tag&&i.kind===e.kind&&i.multi===e.multi&&(t=n)}),i[t]=e}),i}function qe(e){return this.extend(e)}qe.prototype.extend=function(e){var t=[],i=[];if(e instanceof Be)i.push(e);else if(Array.isArray(e))i=i.concat(e);else{if(!e||!Array.isArray(e.implicit)&&!Array.isArray(e.explicit))throw new De("Schema.extend argument should be a Type, [ Type ], or a schema definition ({ implicit: [...], explicit: [...] })");e.implicit&&(t=t.concat(e.implicit)),e.explicit&&(i=i.concat(e.explicit))}t.forEach(function(e){if(!(e instanceof Be))throw new De("Specified list of YAML types (or a single Type object) contains a non-Type object.");if(e.loadKind&&"scalar"!==e.loadKind)throw new De("There is a non-scalar type in the implicit list of a schema. Implicit resolving of such types is not supported.");if(e.multi)throw new De("There is a multi type in the implicit list of a schema. Multi tags can only be listed as explicit.")}),i.forEach(function(e){if(!(e instanceof Be))throw new De("Specified list of YAML types (or a single Type object) contains a non-Type object.")});var n=Object.create(qe.prototype);return n.implicit=(this.implicit||[]).concat(t),n.explicit=(this.explicit||[]).concat(i),n.compiledImplicit=He(n,"implicit"),n.compiledExplicit=He(n,"explicit"),n.compiledTypeMap=function(){var e,t,i={scalar:{},sequence:{},mapping:{},fallback:{},multi:{scalar:[],sequence:[],mapping:[],fallback:[]}};function n(e){e.multi?(i.multi[e.kind].push(e),i.multi.fallback.push(e)):i[e.kind][e.tag]=i.fallback[e.tag]=e}for(e=0,t=arguments.length;e<t;e+=1)arguments[e].forEach(n);return i}(n.compiledImplicit,n.compiledExplicit),n};var Ye=new qe({explicit:[new Be("tag:yaml.org,2002:str",{kind:"scalar",construct:function(e){return null!==e?e:""}}),new Be("tag:yaml.org,2002:seq",{kind:"sequence",construct:function(e){return null!==e?e:[]}}),new Be("tag:yaml.org,2002:map",{kind:"mapping",construct:function(e){return null!==e?e:{}}})]});var Ve=new Be("tag:yaml.org,2002:null",{kind:"scalar",resolve:function(e){if(null===e)return!0;var t=e.length;return 1===t&&"~"===e||4===t&&("null"===e||"Null"===e||"NULL"===e)},construct:function(){return null},predicate:function(e){return null===e},represent:{canonical:function(){return"~"},lowercase:function(){return"null"},uppercase:function(){return"NULL"},camelcase:function(){return"Null"},empty:function(){return""}},defaultStyle:"lowercase"});var Ke=new Be("tag:yaml.org,2002:bool",{kind:"scalar",resolve:function(e){if(null===e)return!1;var t=e.length;return 4===t&&("true"===e||"True"===e||"TRUE"===e)||5===t&&("false"===e||"False"===e||"FALSE"===e)},construct:function(e){return"true"===e||"True"===e||"TRUE"===e},predicate:function(e){return"[object Boolean]"===Object.prototype.toString.call(e)},represent:{lowercase:function(e){return e?"true":"false"},uppercase:function(e){return e?"TRUE":"FALSE"},camelcase:function(e){return e?"True":"False"}},defaultStyle:"lowercase"});function Ge(e){return 48<=e&&e<=57||65<=e&&e<=70||97<=e&&e<=102}function Je(e){return 48<=e&&e<=55}function Ze(e){return 48<=e&&e<=57}var Qe=new Be("tag:yaml.org,2002:int",{kind:"scalar",resolve:function(e){if(null===e)return!1;var t,i=e.length,n=0,r=!1;if(!i)return!1;if("-"!==(t=e[n])&&"+"!==t||(t=e[++n]),"0"===t){if(n+1===i)return!0;if("b"===(t=e[++n])){for(n++;n<i;n++)if("_"!==(t=e[n])){if("0"!==t&&"1"!==t)return!1;r=!0}return r&&"_"!==t}if("x"===t){for(n++;n<i;n++)if("_"!==(t=e[n])){if(!Ge(e.charCodeAt(n)))return!1;r=!0}return r&&"_"!==t}if("o"===t){for(n++;n<i;n++)if("_"!==(t=e[n])){if(!Je(e.charCodeAt(n)))return!1;r=!0}return r&&"_"!==t}}if("_"===t)return!1;for(;n<i;n++)if("_"!==(t=e[n])){if(!Ze(e.charCodeAt(n)))return!1;r=!0}return!(!r||"_"===t)},construct:function(e){var t,i=e,n=1;if(-1!==i.indexOf("_")&&(i=i.replace(/_/g,"")),"-"!==(t=i[0])&&"+"!==t||("-"===t&&(n=-1),t=(i=i.slice(1))[0]),"0"===i)return 0;if("0"===t){if("b"===i[1])return n*parseInt(i.slice(2),2);if("x"===i[1])return n*parseInt(i.slice(2),16);if("o"===i[1])return n*parseInt(i.slice(2),8)}return n*parseInt(i,10)},predicate:function(e){return"[object Number]"===Object.prototype.toString.call(e)&&e%1==0&&!Re.isNegativeZero(e)},represent:{binary:function(e){return e>=0?"0b"+e.toString(2):"-0b"+e.toString(2).slice(1)},octal:function(e){return e>=0?"0o"+e.toString(8):"-0o"+e.toString(8).slice(1)},decimal:function(e){return e.toString(10)},hexadecimal:function(e){return e>=0?"0x"+e.toString(16).toUpperCase():"-0x"+e.toString(16).toUpperCase().slice(1)}},defaultStyle:"decimal",styleAliases:{binary:[2,"bin"],octal:[8,"oct"],decimal:[10,"dec"],hexadecimal:[16,"hex"]}}),Xe=new RegExp("^(?:[-+]?(?:[0-9][0-9_]*)(?:\\.[0-9_]*)?(?:[eE][-+]?[0-9]+)?|\\.[0-9_]+(?:[eE][-+]?[0-9]+)?|[-+]?\\.(?:inf|Inf|INF)|\\.(?:nan|NaN|NAN))$");var et=/^[-+]?[0-9]+e/;var tt=new Be("tag:yaml.org,2002:float",{kind:"scalar",resolve:function(e){return null!==e&&!(!Xe.test(e)||"_"===e[e.length-1])},construct:function(e){var t,i;return i="-"===(t=e.replace(/_/g,"").toLowerCase())[0]?-1:1,"+-".indexOf(t[0])>=0&&(t=t.slice(1)),".inf"===t?1===i?Number.POSITIVE_INFINITY:Number.NEGATIVE_INFINITY:".nan"===t?NaN:i*parseFloat(t,10)},predicate:function(e){return"[object Number]"===Object.prototype.toString.call(e)&&(e%1!=0||Re.isNegativeZero(e))},represent:function(e,t){var i;if(isNaN(e))switch(t){case"lowercase":return".nan";case"uppercase":return".NAN";case"camelcase":return".NaN"}else if(Number.POSITIVE_INFINITY===e)switch(t){case"lowercase":return".inf";case"uppercase":return".INF";case"camelcase":return".Inf"}else if(Number.NEGATIVE_INFINITY===e)switch(t){case"lowercase":return"-.inf";case"uppercase":return"-.INF";case"camelcase":return"-.Inf"}else if(Re.isNegativeZero(e))return"-0.0";return i=e.toString(10),et.test(i)?i.replace("e",".e"):i},defaultStyle:"lowercase"}),it=Ye.extend({implicit:[Ve,Ke,Qe,tt]}),nt=new RegExp("^([0-9][0-9][0-9][0-9])-([0-9][0-9])-([0-9][0-9])$"),rt=new RegExp("^([0-9][0-9][0-9][0-9])-([0-9][0-9]?)-([0-9][0-9]?)(?:[Tt]|[ \\t]+)([0-9][0-9]?):([0-9][0-9]):([0-9][0-9])(?:\\.([0-9]*))?(?:[ \\t]*(Z|([-+])([0-9][0-9]?)(?::([0-9][0-9]))?))?$");var ot=new Be("tag:yaml.org,2002:timestamp",{kind:"scalar",resolve:function(e){return null!==e&&(null!==nt.exec(e)||null!==rt.exec(e))},construct:function(e){var t,i,n,r,o,s,a,l,c=0,d=null;if(null===(t=nt.exec(e))&&(t=rt.exec(e)),null===t)throw new Error("Date resolve error");if(i=+t[1],n=+t[2]-1,r=+t[3],!t[4])return new Date(Date.UTC(i,n,r));if(o=+t[4],s=+t[5],a=+t[6],t[7]){for(c=t[7].slice(0,3);c.length<3;)c+="0";c=+c}return t[9]&&(d=6e4*(60*+t[10]+ +(t[11]||0)),"-"===t[9]&&(d=-d)),l=new Date(Date.UTC(i,n,r,o,s,a,c)),d&&l.setTime(l.getTime()-d),l},instanceOf:Date,represent:function(e){return e.toISOString()}});var st=new Be("tag:yaml.org,2002:merge",{kind:"scalar",resolve:function(e){return"<<"===e||null===e}}),at="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r";var lt=new Be("tag:yaml.org,2002:binary",{kind:"scalar",resolve:function(e){if(null===e)return!1;var t,i,n=0,r=e.length,o=at;for(i=0;i<r;i++)if(!((t=o.indexOf(e.charAt(i)))>64)){if(t<0)return!1;n+=6}return n%8==0},construct:function(e){var t,i,n=e.replace(/[\r\n=]/g,""),r=n.length,o=at,s=0,a=[];for(t=0;t<r;t++)t%4==0&&t&&(a.push(s>>16&255),a.push(s>>8&255),a.push(255&s)),s=s<<6|o.indexOf(n.charAt(t));return 0===(i=r%4*6)?(a.push(s>>16&255),a.push(s>>8&255),a.push(255&s)):18===i?(a.push(s>>10&255),a.push(s>>2&255)):12===i&&a.push(s>>4&255),new Uint8Array(a)},predicate:function(e){return"[object Uint8Array]"===Object.prototype.toString.call(e)},represent:function(e){var t,i,n="",r=0,o=e.length,s=at;for(t=0;t<o;t++)t%3==0&&t&&(n+=s[r>>18&63],n+=s[r>>12&63],n+=s[r>>6&63],n+=s[63&r]),r=(r<<8)+e[t];return 0===(i=o%3)?(n+=s[r>>18&63],n+=s[r>>12&63],n+=s[r>>6&63],n+=s[63&r]):2===i?(n+=s[r>>10&63],n+=s[r>>4&63],n+=s[r<<2&63],n+=s[64]):1===i&&(n+=s[r>>2&63],n+=s[r<<4&63],n+=s[64],n+=s[64]),n}}),ct=Object.prototype.hasOwnProperty,dt=Object.prototype.toString;var ut=new Be("tag:yaml.org,2002:omap",{kind:"sequence",resolve:function(e){if(null===e)return!0;var t,i,n,r,o,s=[],a=e;for(t=0,i=a.length;t<i;t+=1){if(n=a[t],o=!1,"[object Object]"!==dt.call(n))return!1;for(r in n)if(ct.call(n,r)){if(o)return!1;o=!0}if(!o)return!1;if(-1!==s.indexOf(r))return!1;s.push(r)}return!0},construct:function(e){return null!==e?e:[]}}),ht=Object.prototype.toString;var pt=new Be("tag:yaml.org,2002:pairs",{kind:"sequence",resolve:function(e){if(null===e)return!0;var t,i,n,r,o,s=e;for(o=new Array(s.length),t=0,i=s.length;t<i;t+=1){if(n=s[t],"[object Object]"!==ht.call(n))return!1;if(1!==(r=Object.keys(n)).length)return!1;o[t]=[r[0],n[r[0]]]}return!0},construct:function(e){if(null===e)return[];var t,i,n,r,o,s=e;for(o=new Array(s.length),t=0,i=s.length;t<i;t+=1)n=s[t],r=Object.keys(n),o[t]=[r[0],n[r[0]]];return o}}),ft=Object.prototype.hasOwnProperty;var gt=new Be("tag:yaml.org,2002:set",{kind:"mapping",resolve:function(e){if(null===e)return!0;var t,i=e;for(t in i)if(ft.call(i,t)&&null!==i[t])return!1;return!0},construct:function(e){return null!==e?e:{}}}),_t=it.extend({implicit:[ot,st],explicit:[lt,ut,pt,gt]}),bt=Object.prototype.hasOwnProperty,vt=/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x84\x86-\x9F\uFFFE\uFFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]/,mt=/[\x85\u2028\u2029]/,yt=/[,\[\]\{\}]/,$t=/^(?:!|!!|![a-z\-]+!)$/i,wt=/^(?:!|[^,\[\]\{\}])(?:%[0-9a-f]{2}|[0-9a-z\-#;\/\?:@&=\+\$,_\.!~\*'\(\)\[\]])*$/i;function xt(e){return Object.prototype.toString.call(e)}function kt(e){return 10===e||13===e}function At(e){return 9===e||32===e}function Ct(e){return 9===e||32===e||10===e||13===e}function St(e){return 44===e||91===e||93===e||123===e||125===e}function Et(e){var t;return 48<=e&&e<=57?e-48:97<=(t=32|e)&&t<=102?t-97+10:-1}function Ot(e){return 120===e?2:117===e?4:85===e?8:0}function It(e){return 48<=e&&e<=57?e-48:-1}function Nt(e){return 48===e?"\0":97===e?"":98===e?"\b":116===e||9===e?"\t":110===e?"\n":118===e?"\v":102===e?"\f":114===e?"\r":101===e?"":32===e?" ":34===e?'"':47===e?"/":92===e?"\\":78===e?"":95===e?" ":76===e?"\u2028":80===e?"\u2029":""}function Tt(e){return e<=65535?String.fromCharCode(e):String.fromCharCode(55296+(e-65536>>10),56320+(e-65536&1023))}for(var jt=new Array(256),Rt=new Array(256),Pt=0;Pt<256;Pt++)jt[Pt]=Nt(Pt)?1:0,Rt[Pt]=Nt(Pt);function Mt(e,t){this.input=e,this.filename=t.filename||null,this.schema=t.schema||_t,this.onWarning=t.onWarning||null,this.legacy=t.legacy||!1,this.json=t.json||!1,this.listener=t.listener||null,this.implicitTypes=this.schema.compiledImplicit,this.typeMap=this.schema.compiledTypeMap,this.length=e.length,this.position=0,this.line=0,this.lineStart=0,this.lineIndent=0,this.firstTabInLine=-1,this.documents=[]}function Dt(e,t){var i={name:e.filename,buffer:e.input.slice(0,-1),position:e.position,line:e.line,column:e.position-e.lineStart};return i.snippet=Le(i),new De(t,i)}function zt(e,t){throw Dt(e,t)}function Wt(e,t){e.onWarning&&e.onWarning.call(null,Dt(e,t))}var Lt={YAML:function(e,t,i){var n,r,o;null!==e.version&&zt(e,"duplication of %YAML directive"),1!==i.length&&zt(e,"YAML directive accepts exactly one argument"),null===(n=/^([0-9]+)\.([0-9]+)$/.exec(i[0]))&&zt(e,"ill-formed argument of the YAML directive"),r=parseInt(n[1],10),o=parseInt(n[2],10),1!==r&&zt(e,"unacceptable YAML version of the document"),e.version=i[0],e.checkLineBreaks=o<2,1!==o&&2!==o&&Wt(e,"unsupported YAML version of the document")},TAG:function(e,t,i){var n,r;2!==i.length&&zt(e,"TAG directive accepts exactly two arguments"),n=i[0],r=i[1],$t.test(n)||zt(e,"ill-formed tag handle (first argument) of the TAG directive"),bt.call(e.tagMap,n)&&zt(e,'there is a previously declared suffix for "'+n+'" tag handle'),wt.test(r)||zt(e,"ill-formed tag prefix (second argument) of the TAG directive");try{r=decodeURIComponent(r)}catch(t){zt(e,"tag prefix is malformed: "+r)}e.tagMap[n]=r}};function Ut(e,t,i,n){var r,o,s,a;if(t<i){if(a=e.input.slice(t,i),n)for(r=0,o=a.length;r<o;r+=1)9===(s=a.charCodeAt(r))||32<=s&&s<=1114111||zt(e,"expected valid JSON character");else vt.test(a)&&zt(e,"the stream contains non-printable characters");e.result+=a}}function Ft(e,t,i,n){var r,o,s,a;for(Re.isObject(i)||zt(e,"cannot merge mappings; the provided source object is unacceptable"),s=0,a=(r=Object.keys(i)).length;s<a;s+=1)o=r[s],bt.call(t,o)||(t[o]=i[o],n[o]=!0)}function Bt(e,t,i,n,r,o,s,a,l){var c,d;if(Array.isArray(r))for(c=0,d=(r=Array.prototype.slice.call(r)).length;c<d;c+=1)Array.isArray(r[c])&&zt(e,"nested arrays are not supported inside keys"),"object"==typeof r&&"[object Object]"===xt(r[c])&&(r[c]="[object Object]");if("object"==typeof r&&"[object Object]"===xt(r)&&(r="[object Object]"),r=String(r),null===t&&(t={}),"tag:yaml.org,2002:merge"===n)if(Array.isArray(o))for(c=0,d=o.length;c<d;c+=1)Ft(e,t,o[c],i);else Ft(e,t,o,i);else e.json||bt.call(i,r)||!bt.call(t,r)||(e.line=s||e.line,e.lineStart=a||e.lineStart,e.position=l||e.position,zt(e,"duplicated mapping key")),"__proto__"===r?Object.defineProperty(t,r,{configurable:!0,enumerable:!0,writable:!0,value:o}):t[r]=o,delete i[r];return t}function Ht(e){var t;10===(t=e.input.charCodeAt(e.position))?e.position++:13===t?(e.position++,10===e.input.charCodeAt(e.position)&&e.position++):zt(e,"a line break is expected"),e.line+=1,e.lineStart=e.position,e.firstTabInLine=-1}function qt(e,t,i){for(var n=0,r=e.input.charCodeAt(e.position);0!==r;){for(;At(r);)9===r&&-1===e.firstTabInLine&&(e.firstTabInLine=e.position),r=e.input.charCodeAt(++e.position);if(t&&35===r)do{r=e.input.charCodeAt(++e.position)}while(10!==r&&13!==r&&0!==r);if(!kt(r))break;for(Ht(e),r=e.input.charCodeAt(e.position),n++,e.lineIndent=0;32===r;)e.lineIndent++,r=e.input.charCodeAt(++e.position)}return-1!==i&&0!==n&&e.lineIndent<i&&Wt(e,"deficient indentation"),n}function Yt(e){var t,i=e.position;return!(45!==(t=e.input.charCodeAt(i))&&46!==t||t!==e.input.charCodeAt(i+1)||t!==e.input.charCodeAt(i+2)||(i+=3,0!==(t=e.input.charCodeAt(i))&&!Ct(t)))}function Vt(e,t){1===t?e.result+=" ":t>1&&(e.result+=Re.repeat("\n",t-1))}function Kt(e,t){var i,n,r=e.tag,o=e.anchor,s=[],a=!1;if(-1!==e.firstTabInLine)return!1;for(null!==e.anchor&&(e.anchorMap[e.anchor]=s),n=e.input.charCodeAt(e.position);0!==n&&(-1!==e.firstTabInLine&&(e.position=e.firstTabInLine,zt(e,"tab characters must not be used in indentation")),45===n)&&Ct(e.input.charCodeAt(e.position+1));)if(a=!0,e.position++,qt(e,!0,-1)&&e.lineIndent<=t)s.push(null),n=e.input.charCodeAt(e.position);else if(i=e.line,Zt(e,t,3,!1,!0),s.push(e.result),qt(e,!0,-1),n=e.input.charCodeAt(e.position),(e.line===i||e.lineIndent>t)&&0!==n)zt(e,"bad indentation of a sequence entry");else if(e.lineIndent<t)break;return!!a&&(e.tag=r,e.anchor=o,e.kind="sequence",e.result=s,!0)}function Gt(e){var t,i,n,r,o=!1,s=!1;if(33!==(r=e.input.charCodeAt(e.position)))return!1;if(null!==e.tag&&zt(e,"duplication of a tag property"),60===(r=e.input.charCodeAt(++e.position))?(o=!0,r=e.input.charCodeAt(++e.position)):33===r?(s=!0,i="!!",r=e.input.charCodeAt(++e.position)):i="!",t=e.position,o){do{r=e.input.charCodeAt(++e.position)}while(0!==r&&62!==r);e.position<e.length?(n=e.input.slice(t,e.position),r=e.input.charCodeAt(++e.position)):zt(e,"unexpected end of the stream within a verbatim tag")}else{for(;0!==r&&!Ct(r);)33===r&&(s?zt(e,"tag suffix cannot contain exclamation marks"):(i=e.input.slice(t-1,e.position+1),$t.test(i)||zt(e,"named tag handle cannot contain such characters"),s=!0,t=e.position+1)),r=e.input.charCodeAt(++e.position);n=e.input.slice(t,e.position),yt.test(n)&&zt(e,"tag suffix cannot contain flow indicator characters")}n&&!wt.test(n)&&zt(e,"tag name cannot contain such characters: "+n);try{n=decodeURIComponent(n)}catch(t){zt(e,"tag name is malformed: "+n)}return o?e.tag=n:bt.call(e.tagMap,i)?e.tag=e.tagMap[i]+n:"!"===i?e.tag="!"+n:"!!"===i?e.tag="tag:yaml.org,2002:"+n:zt(e,'undeclared tag handle "'+i+'"'),!0}function Jt(e){var t,i;if(38!==(i=e.input.charCodeAt(e.position)))return!1;for(null!==e.anchor&&zt(e,"duplication of an anchor property"),i=e.input.charCodeAt(++e.position),t=e.position;0!==i&&!Ct(i)&&!St(i);)i=e.input.charCodeAt(++e.position);return e.position===t&&zt(e,"name of an anchor node must contain at least one character"),e.anchor=e.input.slice(t,e.position),!0}function Zt(e,t,i,n,r){var o,s,a,l,c,d,u,h,p,f=1,g=!1,_=!1;if(null!==e.listener&&e.listener("open",e),e.tag=null,e.anchor=null,e.kind=null,e.result=null,o=s=a=4===i||3===i,n&&qt(e,!0,-1)&&(g=!0,e.lineIndent>t?f=1:e.lineIndent===t?f=0:e.lineIndent<t&&(f=-1)),1===f)for(;Gt(e)||Jt(e);)qt(e,!0,-1)?(g=!0,a=o,e.lineIndent>t?f=1:e.lineIndent===t?f=0:e.lineIndent<t&&(f=-1)):a=!1;if(a&&(a=g||r),1!==f&&4!==i||(h=1===i||2===i?t:t+1,p=e.position-e.lineStart,1===f?a&&(Kt(e,p)||function(e,t,i){var n,r,o,s,a,l,c,d=e.tag,u=e.anchor,h={},p=Object.create(null),f=null,g=null,_=null,b=!1,v=!1;if(-1!==e.firstTabInLine)return!1;for(null!==e.anchor&&(e.anchorMap[e.anchor]=h),c=e.input.charCodeAt(e.position);0!==c;){if(b||-1===e.firstTabInLine||(e.position=e.firstTabInLine,zt(e,"tab characters must not be used in indentation")),n=e.input.charCodeAt(e.position+1),o=e.line,63!==c&&58!==c||!Ct(n)){if(s=e.line,a=e.lineStart,l=e.position,!Zt(e,i,2,!1,!0))break;if(e.line===o){for(c=e.input.charCodeAt(e.position);At(c);)c=e.input.charCodeAt(++e.position);if(58===c)Ct(c=e.input.charCodeAt(++e.position))||zt(e,"a whitespace character is expected after the key-value separator within a block mapping"),b&&(Bt(e,h,p,f,g,null,s,a,l),f=g=_=null),v=!0,b=!1,r=!1,f=e.tag,g=e.result;else{if(!v)return e.tag=d,e.anchor=u,!0;zt(e,"can not read an implicit mapping pair; a colon is missed")}}else{if(!v)return e.tag=d,e.anchor=u,!0;zt(e,"can not read a block mapping entry; a multiline key may not be an implicit key")}}else 63===c?(b&&(Bt(e,h,p,f,g,null,s,a,l),f=g=_=null),v=!0,b=!0,r=!0):b?(b=!1,r=!0):zt(e,"incomplete explicit mapping pair; a key node is missed; or followed by a non-tabulated empty line"),e.position+=1,c=n;if((e.line===o||e.lineIndent>t)&&(b&&(s=e.line,a=e.lineStart,l=e.position),Zt(e,t,4,!0,r)&&(b?g=e.result:_=e.result),b||(Bt(e,h,p,f,g,_,s,a,l),f=g=_=null),qt(e,!0,-1),c=e.input.charCodeAt(e.position)),(e.line===o||e.lineIndent>t)&&0!==c)zt(e,"bad indentation of a mapping entry");else if(e.lineIndent<t)break}return b&&Bt(e,h,p,f,g,null,s,a,l),v&&(e.tag=d,e.anchor=u,e.kind="mapping",e.result=h),v}(e,p,h))||function(e,t){var i,n,r,o,s,a,l,c,d,u,h,p,f=!0,g=e.tag,_=e.anchor,b=Object.create(null);if(91===(p=e.input.charCodeAt(e.position)))s=93,c=!1,o=[];else{if(123!==p)return!1;s=125,c=!0,o={}}for(null!==e.anchor&&(e.anchorMap[e.anchor]=o),p=e.input.charCodeAt(++e.position);0!==p;){if(qt(e,!0,t),(p=e.input.charCodeAt(e.position))===s)return e.position++,e.tag=g,e.anchor=_,e.kind=c?"mapping":"sequence",e.result=o,!0;f?44===p&&zt(e,"expected the node content, but found ','"):zt(e,"missed comma between flow collection entries"),h=null,a=l=!1,63===p&&Ct(e.input.charCodeAt(e.position+1))&&(a=l=!0,e.position++,qt(e,!0,t)),i=e.line,n=e.lineStart,r=e.position,Zt(e,t,1,!1,!0),u=e.tag,d=e.result,qt(e,!0,t),p=e.input.charCodeAt(e.position),!l&&e.line!==i||58!==p||(a=!0,p=e.input.charCodeAt(++e.position),qt(e,!0,t),Zt(e,t,1,!1,!0),h=e.result),c?Bt(e,o,b,u,d,h,i,n,r):a?o.push(Bt(e,null,b,u,d,h,i,n,r)):o.push(d),qt(e,!0,t),44===(p=e.input.charCodeAt(e.position))?(f=!0,p=e.input.charCodeAt(++e.position)):f=!1}zt(e,"unexpected end of the stream within a flow collection")}(e,h)?_=!0:(s&&function(e,t){var i,n,r,o,s=1,a=!1,l=!1,c=t,d=0,u=!1;if(124===(o=e.input.charCodeAt(e.position)))n=!1;else{if(62!==o)return!1;n=!0}for(e.kind="scalar",e.result="";0!==o;)if(43===(o=e.input.charCodeAt(++e.position))||45===o)1===s?s=43===o?3:2:zt(e,"repeat of a chomping mode identifier");else{if(!((r=It(o))>=0))break;0===r?zt(e,"bad explicit indentation width of a block scalar; it cannot be less than one"):l?zt(e,"repeat of an indentation width identifier"):(c=t+r-1,l=!0)}if(At(o)){do{o=e.input.charCodeAt(++e.position)}while(At(o));if(35===o)do{o=e.input.charCodeAt(++e.position)}while(!kt(o)&&0!==o)}for(;0!==o;){for(Ht(e),e.lineIndent=0,o=e.input.charCodeAt(e.position);(!l||e.lineIndent<c)&&32===o;)e.lineIndent++,o=e.input.charCodeAt(++e.position);if(!l&&e.lineIndent>c&&(c=e.lineIndent),kt(o))d++;else{if(e.lineIndent<c){3===s?e.result+=Re.repeat("\n",a?1+d:d):1===s&&a&&(e.result+="\n");break}for(n?At(o)?(u=!0,e.result+=Re.repeat("\n",a?1+d:d)):u?(u=!1,e.result+=Re.repeat("\n",d+1)):0===d?a&&(e.result+=" "):e.result+=Re.repeat("\n",d):e.result+=Re.repeat("\n",a?1+d:d),a=!0,l=!0,d=0,i=e.position;!kt(o)&&0!==o;)o=e.input.charCodeAt(++e.position);Ut(e,i,e.position,!1)}}return!0}(e,h)||function(e,t){var i,n,r;if(39!==(i=e.input.charCodeAt(e.position)))return!1;for(e.kind="scalar",e.result="",e.position++,n=r=e.position;0!==(i=e.input.charCodeAt(e.position));)if(39===i){if(Ut(e,n,e.position,!0),39!==(i=e.input.charCodeAt(++e.position)))return!0;n=e.position,e.position++,r=e.position}else kt(i)?(Ut(e,n,r,!0),Vt(e,qt(e,!1,t)),n=r=e.position):e.position===e.lineStart&&Yt(e)?zt(e,"unexpected end of the document within a single quoted scalar"):(e.position++,r=e.position);zt(e,"unexpected end of the stream within a single quoted scalar")}(e,h)||function(e,t){var i,n,r,o,s,a;if(34!==(a=e.input.charCodeAt(e.position)))return!1;for(e.kind="scalar",e.result="",e.position++,i=n=e.position;0!==(a=e.input.charCodeAt(e.position));){if(34===a)return Ut(e,i,e.position,!0),e.position++,!0;if(92===a){if(Ut(e,i,e.position,!0),kt(a=e.input.charCodeAt(++e.position)))qt(e,!1,t);else if(a<256&&jt[a])e.result+=Rt[a],e.position++;else if((s=Ot(a))>0){for(r=s,o=0;r>0;r--)(s=Et(a=e.input.charCodeAt(++e.position)))>=0?o=(o<<4)+s:zt(e,"expected hexadecimal character");e.result+=Tt(o),e.position++}else zt(e,"unknown escape sequence");i=n=e.position}else kt(a)?(Ut(e,i,n,!0),Vt(e,qt(e,!1,t)),i=n=e.position):e.position===e.lineStart&&Yt(e)?zt(e,"unexpected end of the document within a double quoted scalar"):(e.position++,n=e.position)}zt(e,"unexpected end of the stream within a double quoted scalar")}(e,h)?_=!0:!function(e){var t,i,n;if(42!==(n=e.input.charCodeAt(e.position)))return!1;for(n=e.input.charCodeAt(++e.position),t=e.position;0!==n&&!Ct(n)&&!St(n);)n=e.input.charCodeAt(++e.position);return e.position===t&&zt(e,"name of an alias node must contain at least one character"),i=e.input.slice(t,e.position),bt.call(e.anchorMap,i)||zt(e,'unidentified alias "'+i+'"'),e.result=e.anchorMap[i],qt(e,!0,-1),!0}(e)?function(e,t,i){var n,r,o,s,a,l,c,d,u=e.kind,h=e.result;if(Ct(d=e.input.charCodeAt(e.position))||St(d)||35===d||38===d||42===d||33===d||124===d||62===d||39===d||34===d||37===d||64===d||96===d)return!1;if((63===d||45===d)&&(Ct(n=e.input.charCodeAt(e.position+1))||i&&St(n)))return!1;for(e.kind="scalar",e.result="",r=o=e.position,s=!1;0!==d;){if(58===d){if(Ct(n=e.input.charCodeAt(e.position+1))||i&&St(n))break}else if(35===d){if(Ct(e.input.charCodeAt(e.position-1)))break}else{if(e.position===e.lineStart&&Yt(e)||i&&St(d))break;if(kt(d)){if(a=e.line,l=e.lineStart,c=e.lineIndent,qt(e,!1,-1),e.lineIndent>=t){s=!0,d=e.input.charCodeAt(e.position);continue}e.position=o,e.line=a,e.lineStart=l,e.lineIndent=c;break}}s&&(Ut(e,r,o,!1),Vt(e,e.line-a),r=o=e.position,s=!1),At(d)||(o=e.position+1),d=e.input.charCodeAt(++e.position)}return Ut(e,r,o,!1),!!e.result||(e.kind=u,e.result=h,!1)}(e,h,1===i)&&(_=!0,null===e.tag&&(e.tag="?")):(_=!0,null===e.tag&&null===e.anchor||zt(e,"alias node should not have any properties")),null!==e.anchor&&(e.anchorMap[e.anchor]=e.result)):0===f&&(_=a&&Kt(e,p))),null===e.tag)null!==e.anchor&&(e.anchorMap[e.anchor]=e.result);else if("?"===e.tag){for(null!==e.result&&"scalar"!==e.kind&&zt(e,'unacceptable node kind for !<?> tag; it should be "scalar", not "'+e.kind+'"'),l=0,c=e.implicitTypes.length;l<c;l+=1)if((u=e.implicitTypes[l]).resolve(e.result)){e.result=u.construct(e.result),e.tag=u.tag,null!==e.anchor&&(e.anchorMap[e.anchor]=e.result);break}}else if("!"!==e.tag){if(bt.call(e.typeMap[e.kind||"fallback"],e.tag))u=e.typeMap[e.kind||"fallback"][e.tag];else for(u=null,l=0,c=(d=e.typeMap.multi[e.kind||"fallback"]).length;l<c;l+=1)if(e.tag.slice(0,d[l].tag.length)===d[l].tag){u=d[l];break}u||zt(e,"unknown tag !<"+e.tag+">"),null!==e.result&&u.kind!==e.kind&&zt(e,"unacceptable node kind for !<"+e.tag+'> tag; it should be "'+u.kind+'", not "'+e.kind+'"'),u.resolve(e.result,e.tag)?(e.result=u.construct(e.result,e.tag),null!==e.anchor&&(e.anchorMap[e.anchor]=e.result)):zt(e,"cannot resolve a node with !<"+e.tag+"> explicit tag")}return null!==e.listener&&e.listener("close",e),null!==e.tag||null!==e.anchor||_}function Qt(e){var t,i,n,r,o=e.position,s=!1;for(e.version=null,e.checkLineBreaks=e.legacy,e.tagMap=Object.create(null),e.anchorMap=Object.create(null);0!==(r=e.input.charCodeAt(e.position))&&(qt(e,!0,-1),r=e.input.charCodeAt(e.position),!(e.lineIndent>0||37!==r));){for(s=!0,r=e.input.charCodeAt(++e.position),t=e.position;0!==r&&!Ct(r);)r=e.input.charCodeAt(++e.position);for(n=[],(i=e.input.slice(t,e.position)).length<1&&zt(e,"directive name must not be less than one character in length");0!==r;){for(;At(r);)r=e.input.charCodeAt(++e.position);if(35===r){do{r=e.input.charCodeAt(++e.position)}while(0!==r&&!kt(r));break}if(kt(r))break;for(t=e.position;0!==r&&!Ct(r);)r=e.input.charCodeAt(++e.position);n.push(e.input.slice(t,e.position))}0!==r&&Ht(e),bt.call(Lt,i)?Lt[i](e,i,n):Wt(e,'unknown document directive "'+i+'"')}qt(e,!0,-1),0===e.lineIndent&&45===e.input.charCodeAt(e.position)&&45===e.input.charCodeAt(e.position+1)&&45===e.input.charCodeAt(e.position+2)?(e.position+=3,qt(e,!0,-1)):s&&zt(e,"directives end mark is expected"),Zt(e,e.lineIndent-1,4,!1,!0),qt(e,!0,-1),e.checkLineBreaks&&mt.test(e.input.slice(o,e.position))&&Wt(e,"non-ASCII line breaks are interpreted as content"),e.documents.push(e.result),e.position===e.lineStart&&Yt(e)?46===e.input.charCodeAt(e.position)&&(e.position+=3,qt(e,!0,-1)):e.position<e.length-1&&zt(e,"end of the stream or a document separator is expected")}var Xt={load:function(e,t){var i=function(e,t){t=t||{},0!==(e=String(e)).length&&(10!==e.charCodeAt(e.length-1)&&13!==e.charCodeAt(e.length-1)&&(e+="\n"),65279===e.charCodeAt(0)&&(e=e.slice(1)));var i=new Mt(e,t),n=e.indexOf("\0");for(-1!==n&&(i.position=n,zt(i,"null byte is not allowed in input")),i.input+="\0";32===i.input.charCodeAt(i.position);)i.lineIndent+=1,i.position+=1;for(;i.position<i.length-1;)Qt(i);return i.documents}(e,t);if(0!==i.length){if(1===i.length)return i[0];throw new De("expected a single document in the stream, but found more")}}},ei=Object.prototype.toString,ti=Object.prototype.hasOwnProperty,ii=65279,ni={0:"\\0",7:"\\a",8:"\\b",9:"\\t",10:"\\n",11:"\\v",12:"\\f",13:"\\r",27:"\\e",34:'\\"',92:"\\\\",133:"\\N",160:"\\_",8232:"\\L",8233:"\\P"},ri=["y","Y","yes","Yes","YES","on","On","ON","n","N","no","No","NO","off","Off","OFF"],oi=/^[-+]?[0-9_]+(?::[0-9_]+)+(?:\.[0-9_]*)?$/;function si(e){var t,i,n;if(t=e.toString(16).toUpperCase(),e<=255)i="x",n=2;else if(e<=65535)i="u",n=4;else{if(!(e<=4294967295))throw new De("code point within a string may not be greater than 0xFFFFFFFF");i="U",n=8}return"\\"+i+Re.repeat("0",n-t.length)+t}function ai(e){this.schema=e.schema||_t,this.indent=Math.max(1,e.indent||2),this.noArrayIndent=e.noArrayIndent||!1,this.skipInvalid=e.skipInvalid||!1,this.flowLevel=Re.isNothing(e.flowLevel)?-1:e.flowLevel,this.styleMap=function(e,t){var i,n,r,o,s,a,l;if(null===t)return{};for(i={},r=0,o=(n=Object.keys(t)).length;r<o;r+=1)s=n[r],a=String(t[s]),"!!"===s.slice(0,2)&&(s="tag:yaml.org,2002:"+s.slice(2)),(l=e.compiledTypeMap.fallback[s])&&ti.call(l.styleAliases,a)&&(a=l.styleAliases[a]),i[s]=a;return i}(this.schema,e.styles||null),this.sortKeys=e.sortKeys||!1,this.lineWidth=e.lineWidth||80,this.noRefs=e.noRefs||!1,this.noCompatMode=e.noCompatMode||!1,this.condenseFlow=e.condenseFlow||!1,this.quotingType='"'===e.quotingType?2:1,this.forceQuotes=e.forceQuotes||!1,this.replacer="function"==typeof e.replacer?e.replacer:null,this.implicitTypes=this.schema.compiledImplicit,this.explicitTypes=this.schema.compiledExplicit,this.tag=null,this.result="",this.duplicates=[],this.usedDuplicates=null}function li(e,t){for(var i,n=Re.repeat(" ",t),r=0,o=-1,s="",a=e.length;r<a;)-1===(o=e.indexOf("\n",r))?(i=e.slice(r),r=a):(i=e.slice(r,o+1),r=o+1),i.length&&"\n"!==i&&(s+=n),s+=i;return s}function ci(e,t){return"\n"+Re.repeat(" ",e.indent*t)}function di(e){return 32===e||9===e}function ui(e){return 32<=e&&e<=126||161<=e&&e<=55295&&8232!==e&&8233!==e||57344<=e&&e<=65533&&e!==ii||65536<=e&&e<=1114111}function hi(e){return ui(e)&&e!==ii&&13!==e&&10!==e}function pi(e,t,i){var n=hi(e),r=n&&!di(e);return(i?n:n&&44!==e&&91!==e&&93!==e&&123!==e&&125!==e)&&35!==e&&!(58===t&&!r)||hi(t)&&!di(t)&&35===e||58===t&&r}function fi(e,t){var i,n=e.charCodeAt(t);return n>=55296&&n<=56319&&t+1<e.length&&(i=e.charCodeAt(t+1))>=56320&&i<=57343?1024*(n-55296)+i-56320+65536:n}function gi(e){return/^\n* /.test(e)}function _i(e,t,i,n,r,o,s,a){var l,c=0,d=null,u=!1,h=!1,p=-1!==n,f=-1,g=function(e){return ui(e)&&e!==ii&&!di(e)&&45!==e&&63!==e&&58!==e&&44!==e&&91!==e&&93!==e&&123!==e&&125!==e&&35!==e&&38!==e&&42!==e&&33!==e&&124!==e&&61!==e&&62!==e&&39!==e&&34!==e&&37!==e&&64!==e&&96!==e}(fi(e,0))&&function(e){return!di(e)&&58!==e}(fi(e,e.length-1));if(t||s)for(l=0;l<e.length;c>=65536?l+=2:l++){if(!ui(c=fi(e,l)))return 5;g=g&&pi(c,d,a),d=c}else{for(l=0;l<e.length;c>=65536?l+=2:l++){if(10===(c=fi(e,l)))u=!0,p&&(h=h||l-f-1>n&&" "!==e[f+1],f=l);else if(!ui(c))return 5;g=g&&pi(c,d,a),d=c}h=h||p&&l-f-1>n&&" "!==e[f+1]}return u||h?i>9&&gi(e)?5:s?2===o?5:2:h?4:3:!g||s||r(e)?2===o?5:2:1}function bi(e,t,i,n,r){e.dump=function(){if(0===t.length)return 2===e.quotingType?'""':"''";if(!e.noCompatMode&&(-1!==ri.indexOf(t)||oi.test(t)))return 2===e.quotingType?'"'+t+'"':"'"+t+"'";var o=e.indent*Math.max(1,i),s=-1===e.lineWidth?-1:Math.max(Math.min(e.lineWidth,40),e.lineWidth-o),a=n||e.flowLevel>-1&&i>=e.flowLevel;switch(_i(t,a,e.indent,s,function(t){return function(e,t){var i,n;for(i=0,n=e.implicitTypes.length;i<n;i+=1)if(e.implicitTypes[i].resolve(t))return!0;return!1}(e,t)},e.quotingType,e.forceQuotes&&!n,r)){case 1:return t;case 2:return"'"+t.replace(/'/g,"''")+"'";case 3:return"|"+vi(t,e.indent)+mi(li(t,o));case 4:return">"+vi(t,e.indent)+mi(li(function(e,t){var i,n,r=/(\n+)([^\n]*)/g,o=(a=e.indexOf("\n"),a=-1!==a?a:e.length,r.lastIndex=a,yi(e.slice(0,a),t)),s="\n"===e[0]||" "===e[0];var a;for(;n=r.exec(e);){var l=n[1],c=n[2];i=" "===c[0],o+=l+(s||i||""===c?"":"\n")+yi(c,t),s=i}return o}(t,s),o));case 5:return'"'+function(e){for(var t,i="",n=0,r=0;r<e.length;n>=65536?r+=2:r++)n=fi(e,r),!(t=ni[n])&&ui(n)?(i+=e[r],n>=65536&&(i+=e[r+1])):i+=t||si(n);return i}(t)+'"';default:throw new De("impossible error: invalid scalar style")}}()}function vi(e,t){var i=gi(e)?String(t):"",n="\n"===e[e.length-1];return i+(n&&("\n"===e[e.length-2]||"\n"===e)?"+":n?"":"-")+"\n"}function mi(e){return"\n"===e[e.length-1]?e.slice(0,-1):e}function yi(e,t){if(""===e||" "===e[0])return e;for(var i,n,r=/ [^ ]/g,o=0,s=0,a=0,l="";i=r.exec(e);)(a=i.index)-o>t&&(n=s>o?s:a,l+="\n"+e.slice(o,n),o=n+1),s=a;return l+="\n",e.length-o>t&&s>o?l+=e.slice(o,s)+"\n"+e.slice(s+1):l+=e.slice(o),l.slice(1)}function $i(e,t,i,n){var r,o,s,a="",l=e.tag;for(r=0,o=i.length;r<o;r+=1)s=i[r],e.replacer&&(s=e.replacer.call(i,String(r),s)),(xi(e,t+1,s,!0,!0,!1,!0)||void 0===s&&xi(e,t+1,null,!0,!0,!1,!0))&&(n&&""===a||(a+=ci(e,t)),e.dump&&10===e.dump.charCodeAt(0)?a+="-":a+="- ",a+=e.dump);e.tag=l,e.dump=a||"[]"}function wi(e,t,i){var n,r,o,s,a,l;for(o=0,s=(r=i?e.explicitTypes:e.implicitTypes).length;o<s;o+=1)if(((a=r[o]).instanceOf||a.predicate)&&(!a.instanceOf||"object"==typeof t&&t instanceof a.instanceOf)&&(!a.predicate||a.predicate(t))){if(i?a.multi&&a.representName?e.tag=a.representName(t):e.tag=a.tag:e.tag="?",a.represent){if(l=e.styleMap[a.tag]||a.defaultStyle,"[object Function]"===ei.call(a.represent))n=a.represent(t,l);else{if(!ti.call(a.represent,l))throw new De("!<"+a.tag+'> tag resolver accepts not "'+l+'" style');n=a.represent[l](t,l)}e.dump=n}return!0}return!1}function xi(e,t,i,n,r,o,s){e.tag=null,e.dump=i,wi(e,i,!1)||wi(e,i,!0);var a,l=ei.call(e.dump),c=n;n&&(n=e.flowLevel<0||e.flowLevel>t);var d,u,h="[object Object]"===l||"[object Array]"===l;if(h&&(u=-1!==(d=e.duplicates.indexOf(i))),(null!==e.tag&&"?"!==e.tag||u||2!==e.indent&&t>0)&&(r=!1),u&&e.usedDuplicates[d])e.dump="*ref_"+d;else{if(h&&u&&!e.usedDuplicates[d]&&(e.usedDuplicates[d]=!0),"[object Object]"===l)n&&0!==Object.keys(e.dump).length?(!function(e,t,i,n){var r,o,s,a,l,c,d="",u=e.tag,h=Object.keys(i);if(!0===e.sortKeys)h.sort();else if("function"==typeof e.sortKeys)h.sort(e.sortKeys);else if(e.sortKeys)throw new De("sortKeys must be a boolean or a function");for(r=0,o=h.length;r<o;r+=1)c="",n&&""===d||(c+=ci(e,t)),a=i[s=h[r]],e.replacer&&(a=e.replacer.call(i,s,a)),xi(e,t+1,s,!0,!0,!0)&&((l=null!==e.tag&&"?"!==e.tag||e.dump&&e.dump.length>1024)&&(e.dump&&10===e.dump.charCodeAt(0)?c+="?":c+="? "),c+=e.dump,l&&(c+=ci(e,t)),xi(e,t+1,a,!0,l)&&(e.dump&&10===e.dump.charCodeAt(0)?c+=":":c+=": ",d+=c+=e.dump));e.tag=u,e.dump=d||"{}"}(e,t,e.dump,r),u&&(e.dump="&ref_"+d+e.dump)):(!function(e,t,i){var n,r,o,s,a,l="",c=e.tag,d=Object.keys(i);for(n=0,r=d.length;n<r;n+=1)a="",""!==l&&(a+=", "),e.condenseFlow&&(a+='"'),s=i[o=d[n]],e.replacer&&(s=e.replacer.call(i,o,s)),xi(e,t,o,!1,!1)&&(e.dump.length>1024&&(a+="? "),a+=e.dump+(e.condenseFlow?'"':"")+":"+(e.condenseFlow?"":" "),xi(e,t,s,!1,!1)&&(l+=a+=e.dump));e.tag=c,e.dump="{"+l+"}"}(e,t,e.dump),u&&(e.dump="&ref_"+d+" "+e.dump));else if("[object Array]"===l)n&&0!==e.dump.length?(e.noArrayIndent&&!s&&t>0?$i(e,t-1,e.dump,r):$i(e,t,e.dump,r),u&&(e.dump="&ref_"+d+e.dump)):(!function(e,t,i){var n,r,o,s="",a=e.tag;for(n=0,r=i.length;n<r;n+=1)o=i[n],e.replacer&&(o=e.replacer.call(i,String(n),o)),(xi(e,t,o,!1,!1)||void 0===o&&xi(e,t,null,!1,!1))&&(""!==s&&(s+=","+(e.condenseFlow?"":" ")),s+=e.dump);e.tag=a,e.dump="["+s+"]"}(e,t,e.dump),u&&(e.dump="&ref_"+d+" "+e.dump));else{if("[object String]"!==l){if("[object Undefined]"===l)return!1;if(e.skipInvalid)return!1;throw new De("unacceptable kind of an object to dump "+l)}"?"!==e.tag&&bi(e,e.dump,t,o,c)}null!==e.tag&&"?"!==e.tag&&(a=encodeURI("!"===e.tag[0]?e.tag.slice(1):e.tag).replace(/!/g,"%21"),a="!"===e.tag[0]?"!"+a:"tag:yaml.org,2002:"===a.slice(0,18)?"!!"+a.slice(18):"!<"+a+">",e.dump=a+" "+e.dump)}return!0}function ki(e,t){var i,n,r=[],o=[];for(Ai(e,r,o),i=0,n=o.length;i<n;i+=1)t.duplicates.push(r[o[i]]);t.usedDuplicates=new Array(n)}function Ai(e,t,i){var n,r,o;if(null!==e&&"object"==typeof e)if(-1!==(r=t.indexOf(e)))-1===i.indexOf(r)&&i.push(r);else if(t.push(e),Array.isArray(e))for(r=0,o=e.length;r<o;r+=1)Ai(e[r],t,i);else for(r=0,o=(n=Object.keys(e)).length;r<o;r+=1)Ai(e[n[r]],t,i)}var Ci=Xt.load,Si={dump:function(e,t){var i=new ai(t=t||{});i.noRefs||ki(e,i);var n=e;return i.replacer&&(n=i.replacer.call({"":n},"",n)),xi(i,0,n,!0,!0)?i.dump+"\n":""}}.dump;const Ei={condition:"state"};let Oi=class extends ae{constructor(){super(...arguments),this.value=[],this.disabled=!1,this.language="en",this._errors={},this._onAdd=()=>{this._emit([...this.value,{...Ei}])}}get hasError(){return Object.keys(this._errors).length>0}render(){return B`
      <div class="wrap">
        <div class="help">${ge(this.language,"conditions_help")}</div>
        ${this.value.map((e,t)=>this._row(e,t))}
        <button
          class="add-condition"
          ?disabled=${this.disabled}
          @click=${this._onAdd}
        >
          ${ge(this.language,"add_condition")}
        </button>
      </div>
    `}_row(e,t){const i=this._errors[t];return B`
      <div class="condition-row">
        <div class="body">
          <textarea
            .value=${Si(e).trimEnd()}
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
          ${ge(this.language,"remove_condition")}
        </button>
      </div>
    `}_emit(e){this.dispatchEvent(new CustomEvent("condition-changed",{detail:{value:e}}))}_setError(e,t){const i={...this._errors};null===t?delete i[e]:i[e]=t,this._errors=i}_onEdit(e,t){const i=e.target.value;let n;try{n=Ci(i)}catch{return void this._setError(t,ge(this.language,"condition_unparseable"))}if(null===n||"object"!=typeof n||Array.isArray(n))return void this._setError(t,ge(this.language,"condition_not_a_mapping"));this._setError(t,null);const r=[...this.value];r[t]=n,this._emit(r)}_onRemove(e){const t={};for(const[i,n]of Object.entries(this._errors)){const r=Number(i);r<e?t[r]=n:r>e&&(t[r-1]=n)}this._errors=t,this._emit(this.value.filter((t,i)=>i!==e))}};Oi.styles=s`
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
  `,e([he({attribute:!1})],Oi.prototype,"value",void 0),e([he({type:Boolean})],Oi.prototype,"disabled",void 0),e([he()],Oi.prototype,"language",void 0),e([pe()],Oi.prototype,"_errors",void 0),Oi=e([ce("shabbat-condition-editor")],Oi);let Ii=class extends ae{constructor(){super(...arguments),this.hass=null,this.value={enabled:!1},this.disabled=!1,this.language="en",this._onEnabled=e=>{const t=Boolean(e.detail?.value);this._emit(t?{enabled:!0,within:this.value.within??"01:00:00"}:{enabled:!1})},this._onWithin=e=>{const t=e.detail?.value;var i;this._emit(void 0===t?{enabled:!0}:{enabled:!0,within:(i=t,[i?.hours??0,i?.minutes??0,i?.seconds??0].map(e=>String(e).padStart(2,"0")).join(":"))})}}render(){return B`
      <div class="wrap">
        <div class="field">
          <label for="replay-enabled">
            ${ge(this.language,"replay_after_restart")}
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
                ${ge(this.language,"replay_within_label")}
              </label>
              <ha-selector
                id="replay-within"
                class="replay-within"
                .hass=${this.hass}
                .selector=${{duration:{}}}
                .value=${function(e){if(void 0===e)return;const t=e.split(":");if(3!==t.length)return;if(!t.every(e=>/^\d+$/.test(e)))return;const[i,n,r]=t.map(e=>Number(e));return{hours:i,minutes:n,seconds:r}}(this.value.within)}
                .disabled=${this.disabled}
                @value-changed=${this._onWithin}
              ></ha-selector>
            </div>`:B`<div class="help">${ge(this.language,"replay_help")}</div>`}
      </div>
    `}_emit(e){this.dispatchEvent(new CustomEvent("replay-changed",{detail:{value:e}}))}};Ii.styles=s`
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
  `,e([he({attribute:!1})],Ii.prototype,"hass",void 0),e([he({attribute:!1})],Ii.prototype,"value",void 0),e([he({type:Boolean})],Ii.prototype,"disabled",void 0),e([he()],Ii.prototype,"language",void 0),Ii=e([ce("shabbat-replay-editor")],Ii);let Ni=class extends ae{constructor(){super(...arguments),this.hass=null,this.action="",this.data={},this.disabled=!1,this._onChange=e=>{const t=e.detail?.value??{},i={action:"string"==typeof t.action?t.action:""};"object"==typeof t.data&&null!==t.data&&(i.data=t.data),this.dispatchEvent(new CustomEvent("service-changed",{detail:i}))},this._observer=null}render(){return B`
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
          .value=${{action:this.action,data:this.data}}
          .disabled=${this.disabled}
          @value-changed=${this._onChange}
        ></ha-service-control>
      </div>
    `}get _control(){return this.shadowRoot?.querySelector("ha-service-control")??null}async updated(){const e=this._control;e?.updateComplete&&await e.updateComplete,this.suppressTargetRows(),this._watch()}disconnectedCallback(){super.disconnectedCallback(),this._observer?.disconnect(),this._observer=null}_watch(){const e=this._control?.shadowRoot;!this._observer&&e&&(this._observer=new MutationObserver(()=>this.suppressTargetRows()),this._observer.observe(e,{childList:!0}))}suppressTargetRows(){const e=this._control?.shadowRoot;if(!e)return 0;const t=[...e.querySelectorAll("ha-selector")].filter(e=>{const t=e.selector;return"object"==typeof t&&null!==t&&"target"in t});for(const e of t)e.style.setProperty("display","none","important");return this.setAttribute("data-target-rows-suppressed",String(t.length)),t.length}};Ni.styles=s`
    :host { display: block; }
  `,e([he({attribute:!1})],Ni.prototype,"hass",void 0),e([he()],Ni.prototype,"action",void 0),e([he({attribute:!1})],Ni.prototype,"data",void 0),e([he({type:Boolean})],Ni.prototype,"disabled",void 0),Ni=e([ce("shabbat-service-editor")],Ni);let Ti=class extends ae{constructor(){super(...arguments),this.hass=null,this.value={},this.inherited={},this.disabled=!1,this.language="en",this._onChange=e=>{const t=e.detail?.value??{};this.dispatchEvent(new CustomEvent("target-changed",{detail:{value:t}}))}}render(){const e=ye(this.value),t=ye(this.inherited),i=""===e&&""!==t;return B`
      <div class="wrap">
        <ha-selector
          .hass=${this.hass}
          .selector=${{target:{}}}
          .value=${this.value}
          .disabled=${this.disabled}
          @value-changed=${this._onChange}
        ></ha-selector>
        ${i?B`<div class="note inherited">
              ${ge(this.language,"inherits_target_from_defaults")}
              ${t}
            </div>`:""===e?B`<div class="note empty">${ge(this.language,"target_none")}</div>`:q}
      </div>
    `}};Ti.styles=s`
    .note {
      color: var(--secondary-text-color, #666);
      font-size: 0.85em;
      margin-block-start: 4px;
      overflow-wrap: anywhere;
    }
  `,e([he({attribute:!1})],Ti.prototype,"hass",void 0),e([he({attribute:!1})],Ti.prototype,"value",void 0),e([he({attribute:!1})],Ti.prototype,"inherited",void 0),e([he({type:Boolean})],Ti.prototype,"disabled",void 0),e([he()],Ti.prototype,"language",void 0),Ti=e([ce("shabbat-target-editor")],Ti);const ji={day:"erev",time:"",action:"",target:{},data:{},condition:[],replay:{enabled:!1},name:null,icon:null,color:null,enabled:!0};let Ri=class extends ae{constructor(){super(...arguments),this.hass=null,this.rule=null,this.seed=null,this.day="erev",this.profile=1,this.defaults={},this.canWrite=!1,this.busy=!1,this.error=null,this.language="en",this.runNowResult=null,this._form=ji,this._advanced=!1,this._conditionError=!1,this._runConfirmOpen=!1,this._seeded=null}willUpdate(){const e=this.rule?`edit:${this.rule.id}`:`new:${this.day}:${this.profile}:${JSON.stringify(this.seed)}`;var t;this._seeded!==e&&(this._seeded=e,this.rule?this._form={day:(t=this.rule).day,time:t.time,action:t.action,target:{...t.target},data:{...t.data},condition:t.condition.map(e=>({...e})),replay:{...t.replay},name:t.name,icon:t.icon,color:t.color,enabled:t.enabled}:this.seed?this._form={...this.seed,day:this.day}:this._form={...ji,day:this.day},this._advanced=!1,this._runConfirmOpen=!1)}_patch(e){this._form={...this._form,...e}}_emit(e){this.dispatchEvent(new CustomEvent(e,{detail:{form:this._form,rule:this.rule}}))}_text(e,t){return B`
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
        <label for="time">${ge(this.language,"time")}</label>
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
    `}_enabledField(){return B`
      <div class="field">
        <label for="enabled">${ge(this.language,"enabled")}</label>
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
        <label for="icon">${ge(this.language,"icon")}</label>
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
      <div class="field">
        <label for="color">${ge(this.language,"colour")}</label>
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
          <h2>${ge(this.language,e?"edit_rule":"add_rule")}</h2>

          ${this.canWrite?q:B`<div class="note">${ge(this.language,"read_only")}</div>`}
          ${this.rule?.migration_error?B`<div class="migration">
                ${ge(this.language,"migration_error")} ${this.rule.migration_error}
              </div>`:q}
          ${null!==this.error?B`<div class="error">${this.error}</div>`:q}
          ${this._conditionError?B`<div class="error condition-blocked">
                ${ge(this.language,"condition_unparseable")}
              </div>`:q}

          <div class="form">
            ${this._timeField()}
            ${this._text("name",ge(this.language,"name"))}

            ${this._enabledField()}

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

            <shabbat-condition-editor
              .value=${this._form.condition}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @condition-changed=${e=>{const t=e.target;this._conditionError=!0===t.hasError,this._patch({condition:e.detail.value})}}
            ></shabbat-condition-editor>

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
              ${ge(this.language,"advanced")}
            </button>
            ${this._advanced?B`
                  <div class="advanced">
                    ${this._iconField()}
                    ${this._colorField()}
                  </div>
                `:q}
          </div>

          <div class="actions">
            ${this.canWrite&&e?B`<button
                  class="delete"
                  ?disabled=${this.busy}
                  @click=${()=>this._emit("dialog-delete")}
                >
                  ${ge(this.language,"delete_rule")}
                </button>`:q}
            <button @click=${()=>this.dispatchEvent(new CustomEvent("dialog-close"))}>
              ${ge(this.language,"cancel")}
            </button>
            ${this.canWrite&&e?B`<button
                  class="duplicate"
                  ?disabled=${this.busy}
                  @click=${()=>this._emit("dialog-duplicate")}
                >
                  ${ge(this.language,"duplicate")}
                </button>`:q}
            ${this.canWrite&&e?B`<button
                  class="run-now"
                  ?disabled=${this.busy}
                  @click=${()=>{this._runConfirmOpen=!this._runConfirmOpen}}
                >
                  ▶ ${ge(this.language,"run_now_button")}
                </button>`:q}
            ${this.canWrite?B`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${()=>this._onSave()}
                >
                  ${ge(this.language,"save")}
                </button>`:q}
          </div>
          ${this._runConfirmOpen?B`<div class="run-confirm">
                <button
                  class="run-simulate"
                  @click=${()=>this._emitRunNow(!0)}
                >${ge(this.language,"run_now_simulate")}</button>
                <button
                  class="run-real"
                  @click=${()=>this._emitRunNow(!1)}
                >${ge(this.language,"run_now_real")}</button>
              </div>`:q}
          ${null!==this.rule&&this.runNowResult?.ruleId===this.rule.id?B`<div class="run-now-result">
                ${(t=this.runNowResult,i=this.language,[xe(Ae(t.results,t.at),i)]).map(e=>B`<div>${e}</div>`)}
              </div>`:q}
        </div>
      </div>
    `;var t,i}};Ri.styles=s`
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
    h2 { margin-block: 0 12px; font-size: 1.1em; }
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 7em; }
    input, select {
      font: inherit;
      padding-block: 4px;
      padding-inline: 6px;
      flex: 1;
      min-inline-size: 0;
    }
    .actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      margin-block-start: 16px;
      flex-wrap: wrap;
    }
    .actions .delete { margin-inline-end: auto; color: var(--error-color, #d64545); }
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
    .error {
      color: var(--error-color, #d64545);
      margin-block: 8px;
      font-size: 0.9em;
    }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    .migration {
      color: var(--error-color, #d64545);
      margin-block: 8px;
      font-size: 0.9em;
      overflow-wrap: anywhere;
    }
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
  `,e([he({attribute:!1})],Ri.prototype,"hass",void 0),e([he({attribute:!1})],Ri.prototype,"rule",void 0),e([he({attribute:!1})],Ri.prototype,"seed",void 0),e([he()],Ri.prototype,"day",void 0),e([he({type:Number})],Ri.prototype,"profile",void 0),e([he({attribute:!1})],Ri.prototype,"defaults",void 0),e([he({type:Boolean})],Ri.prototype,"canWrite",void 0),e([he({type:Boolean})],Ri.prototype,"busy",void 0),e([he()],Ri.prototype,"error",void 0),e([he()],Ri.prototype,"language",void 0),e([he({attribute:!1})],Ri.prototype,"runNowResult",void 0),e([pe()],Ri.prototype,"_form",void 0),e([pe()],Ri.prototype,"_advanced",void 0),e([pe()],Ri.prototype,"_conditionError",void 0),e([pe()],Ri.prototype,"_runConfirmOpen",void 0),Ri=e([ce("shabbat-rule-dialog")],Ri);let Pi=class extends ae{constructor(){super(...arguments),this.hass=null,this.defaults={},this.canWrite=!1,this.busy=!1,this.error=null,this.language="en",this._draft={},this._action="",this._seeded=!1,this._onServiceChanged=e=>{const t=e.detail;this._action="string"==typeof t.action?t.action:"","data"in t&&(this._draft={...this._draft,data:t.data})}}willUpdate(){this._seeded||(this._seeded=!0,this._draft={target:this.defaults.target??{},data:this.defaults.data??{}})}_onSave(){this.dispatchEvent(new CustomEvent("dialog-save",{detail:{defaults:{target:this._draft.target??{},data:this._draft.data??{}}}}))}render(){return B`
      <div class="sheet" @click=${e=>{e.target===e.currentTarget&&this.dispatchEvent(new CustomEvent("dialog-close"))}}>
        <div class="panel">
          <h2>${ge(this.language,"defaults_title")}</h2>
          <div class="note">${ge(this.language,"defaults_help")}</div>
          ${null!==this.error?B`<div class="error">${this.error}</div>`:q}

          <div class="form">
            <div class="section">
              <div class="label">${ge(this.language,"target")}</div>
              <shabbat-target-editor
                .hass=${this.hass}
                .value=${this._draft.target??{}}
                .disabled=${!this.canWrite}
                .language=${this.language}
                @target-changed=${e=>{this._draft={...this._draft,target:e.detail.value}}}
              ></shabbat-target-editor>
            </div>
            <div class="section">
              <div class="label">${ge(this.language,"data")}</div>
              <shabbat-service-editor
                .hass=${this.hass}
                .action=${this._action}
                .data=${this._draft.data??{}}
                .disabled=${!this.canWrite}
                @service-changed=${this._onServiceChanged}
              ></shabbat-service-editor>
            </div>
          </div>

          <div class="actions">
            <button @click=${()=>this.dispatchEvent(new CustomEvent("dialog-close"))}>
              ${ge(this.language,"cancel")}
            </button>
            ${this.canWrite?B`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${()=>this._onSave()}
                >
                  ${ge(this.language,"save")}
                </button>`:q}
          </div>
        </div>
      </div>
    `}};function Mi(e){const t=["erev"];for(let i=1;i<=e;i+=1)t.push(String(i));return t}Pi.styles=s`
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
  `,e([he({attribute:!1})],Pi.prototype,"hass",void 0),e([he({attribute:!1})],Pi.prototype,"defaults",void 0),e([he({type:Boolean})],Pi.prototype,"canWrite",void 0),e([he({type:Boolean})],Pi.prototype,"busy",void 0),e([he()],Pi.prototype,"error",void 0),e([he()],Pi.prototype,"language",void 0),e([pe()],Pi.prototype,"_draft",void 0),e([pe()],Pi.prototype,"_action",void 0),Pi=e([ce("shabbat-defaults-dialog")],Pi);let Di=class extends ae{constructor(){super(...arguments),this.hass=null,this.language="en",this.canWrite=!1,this._profile=1,this._day="erev",this._forceConditions=!1,this._preview=null,this._busy=!1,this._error=null,this._results=null}connectedCallback(){super.connectedCallback(),this._loadPreview()}async _loadPreview(){if(null!==this.hass){this._busy=!0;try{this._preview=await this.hass.callWS({type:"shabbat_scheduler/preview",block_length:this._profile})}catch(e){const t=e;this._error=t?.message??String(e)}finally{this._busy=!1}}}_previewRules(){return this._preview?.rules??[]}async _run(e){if(null!==this.hass){this._busy=!0,this._error=null;try{const t=await this.hass.callWS({type:"shabbat_scheduler/rules/run_day",profile:this._profile,day:this._day,simulate:e,force_conditions:this._forceConditions});this._results=t.results.map(e=>({ruleId:e.rule_id,results:e.results}))}catch(e){const t=e;this._error=t?.message??String(e)}finally{this._busy=!1}}}_dayLabel(e){return"erev"===e?ge(this.language,"erev"):`${ge(this.language,"day")} ${e}`}render(){return B`
      <div class="sheet" @click=${e=>{e.target===e.currentTarget&&this.dispatchEvent(new CustomEvent("dialog-close"))}}>
        <div class="panel">
          <h2>${ge(this.language,"simulate_title")}</h2>
          ${null!==this._error?B`<div class="error">${this._error}</div>`:q}

          <div class="field">
            <label>${ge(this.language,"simulate_profile")}</label>
            <select
              class="profile"
              .value=${String(this._profile)}
              @change=${e=>{this._profile=Number(e.target.value),Mi(this._profile).includes(this._day)||(this._day="erev"),this._loadPreview()}}
            >
              ${[1,2,3].map(e=>B`<option value=${e}>${e}d</option>`)}
            </select>
          </div>
          <div class="field">
            <label>${ge(this.language,"simulate_day")}</label>
            <select
              class="day"
              .value=${this._day}
              @change=${e=>{this._day=e.target.value}}
            >
              ${Mi(this._profile).map(e=>B`<option value=${e}>${this._dayLabel(e)}</option>`)}
            </select>
          </div>
          <div class="field">
            <label>${ge(this.language,"simulate_force_conditions")}</label>
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
                ${this._results.map(e=>{const t=Ae(e.results,(new Date).toISOString());return B`<div class="row">
                    ${e.ruleId}: ${xe(t,this.language)}
                  </div>`})}
              </div>`:q}

          <div class="actions">
            <button @click=${()=>this.dispatchEvent(new CustomEvent("dialog-close"))}>
              ${ge(this.language,"cancel")}
            </button>
            ${this.canWrite?B`<button
                  class="run-simulate"
                  ?disabled=${this._busy}
                  @click=${()=>this._run(!0)}
                >${ge(this.language,"simulate_this_day")}</button>
                <button
                  class="run-real"
                  ?disabled=${this._busy}
                  @click=${()=>this._run(!1)}
                >${ge(this.language,"simulate_run_for_real")}</button>`:q}
          </div>
        </div>
      </div>
    `}};function zi(e){const t=["erev"];for(let i=1;i<=e;i+=1)t.push(String(i));return t}Di.styles=s`
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
  `,e([he({attribute:!1})],Di.prototype,"hass",void 0),e([he()],Di.prototype,"language",void 0),e([he({type:Boolean})],Di.prototype,"canWrite",void 0),e([pe()],Di.prototype,"_profile",void 0),e([pe()],Di.prototype,"_day",void 0),e([pe()],Di.prototype,"_forceConditions",void 0),e([pe()],Di.prototype,"_preview",void 0),e([pe()],Di.prototype,"_busy",void 0),e([pe()],Di.prototype,"_error",void 0),e([pe()],Di.prototype,"_results",void 0),Di=e([ce("shabbat-simulate-dialog")],Di);let Wi=class extends ae{constructor(){super(...arguments),this.source=null,this.rules=[],this.busy=!1,this.error=null,this.landed=null,this.failed=null,this.language="en",this._targetProfile=1,this._targetDay="erev",this._mode="extend",this._seeded=null}willUpdate(){const e=this.source?`${this.source.scope}:${this.source.profile}:${this.source.day??""}`:null;e!==this._seeded&&(this._seeded=e,this._targetProfile=this.source?.profile??1,this._targetDay=this.source?.day??"erev",this._mode="extend")}get _dayScope(){return"day"===this.source?.scope}_sourceRuleIds(){return null===this.source?[]:this._dayScope?this.rules.filter(e=>e.profile===this.source.profile&&e.day===this.source.day).map(e=>e.id):this.rules.filter(e=>e.profile===this.source.profile).map(e=>e.id)}_idsToSend(){return null!==this.failed&&this.failed.length>0?this.failed:this._sourceRuleIds()}_targetRuleCount(){return this._dayScope?this.rules.filter(e=>e.profile===this._targetProfile&&e.day===this._targetDay).length:this.rules.filter(e=>e.profile===this._targetProfile).length}_title(){if(null===this.source)return"";if(this._dayScope){const e="erev"===this.source.day?ge(this.language,"erev"):`${ge(this.language,"day")} ${this.source.day}`;return`${ge(this.language,"clone_day_prefix")} ${e}`}return`${ge(this.language,"clone_profile_prefix")} ${this.source.profile}${ge(this.language,"clone_profile_suffix")}`}_onConfirm(){this.dispatchEvent(new CustomEvent("dialog-clone-confirm",{detail:{sourceRuleIds:this._idsToSend(),sourceProfile:this.source?.profile,sourceScope:this.source?.scope,targetProfile:this._targetProfile,targetDay:this._dayScope?this._targetDay:void 0,mode:this._mode}}))}render(){if(null===this.source)return q;const e=0===this._idsToSend().length,t=this._targetRuleCount();return B`
      <div class="sheet" @click=${e=>{e.target===e.currentTarget&&this.dispatchEvent(new CustomEvent("dialog-close"))}}>
        <div class="panel">
          <h2>${this._title()}</h2>
          ${null!==this.error?B`<div class="error">${this.error}</div>`:q}
          ${null!==this.landed?B`<div class="report">
                ${ge(this.language,"clone_landed")}: ${this.landed.join(", ")||ge(this.language,"clone_none")}
                ${this.failed&&this.failed.length?B`<br />${ge(this.language,"clone_failed")}: ${this.failed.join(", ")}`:q}
              </div>`:q}

          <div class="field">
            <label>${ge(this.language,"clone_target_profile")}</label>
            <select
              class="target-profile"
              .value=${String(this._targetProfile)}
              @change=${e=>{this._targetProfile=Number(e.target.value),this._dayScope&&!zi(this._targetProfile).includes(this._targetDay)&&(this._targetDay="erev")}}
            >
              ${[1,2,3].map(e=>B`<option value=${e}>${e}d</option>`)}
            </select>
          </div>
          ${this._dayScope?B`<div class="field">
                <label>${ge(this.language,"clone_target_day")}</label>
                <select
                  class="target-day"
                  .value=${this._targetDay}
                  @change=${e=>{this._targetDay=e.target.value}}
                >
                  ${zi(this._targetProfile).map(e=>B`<option value=${e}>
                      ${"erev"===e?ge(this.language,"erev"):`${ge(this.language,"day")} ${e}`}
                    </option>`)}
                </select>
              </div>`:q}

          <div class="field">
            <button
              class="mode extend ${"extend"===this._mode?"active":""}"
              @click=${()=>{this._mode="extend"}}
            >${ge(this.language,"clone_extend")}</button>
            <button
              class="mode overwrite ${"overwrite"===this._mode?"active":""}"
              @click=${()=>{this._mode="overwrite"}}
            >${ge(this.language,"clone_overwrite")}</button>
          </div>

          ${t>0?B`<div class="warning">${ge(this.language,"clone_target_has_rules")} ${t}</div>`:q}

          <div class="actions">
            <button @click=${()=>this.dispatchEvent(new CustomEvent("dialog-close"))}>
              ${ge(this.language,"cancel")}
            </button>
            <button
              class="confirm"
              ?disabled=${this.busy||e}
              @click=${()=>this._onConfirm()}
            >${ge(this.language,"clone_confirm")}</button>
          </div>
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
    .field label { min-inline-size: 7em; }
    select { font: inherit; padding-block: 4px; padding-inline: 6px; flex: 1; }
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
  `,e([he({attribute:!1})],Wi.prototype,"source",void 0),e([he({attribute:!1})],Wi.prototype,"rules",void 0),e([he({type:Boolean})],Wi.prototype,"busy",void 0),e([he()],Wi.prototype,"error",void 0),e([he({attribute:!1})],Wi.prototype,"landed",void 0),e([he({attribute:!1})],Wi.prototype,"failed",void 0),e([he()],Wi.prototype,"language",void 0),e([pe()],Wi.prototype,"_targetProfile",void 0),e([pe()],Wi.prototype,"_targetDay",void 0),e([pe()],Wi.prototype,"_mode",void 0),Wi=e([ce("shabbat-clone-dialog")],Wi);const Li="not_set_up";let Ui=class extends ae{constructor(){super(...arguments),this._state=null,this._error=null,this._config={},this._selectedProfile=null,this._editing=null,this._creatingDay=null,this._defaultsOpen=!1,this._simulateOpen=!1,this._dialogError=null,this._toggleErrors={},this._busy=!1,this._duplicateSeed=null,this._runNowResult=null,this._cloneSource=null,this._cloneLanded=null,this._cloneFailed=null,this._unsubscribe=null,this._subscribed=!1,this._generation=0,this._onMaster=e=>{const{enabled:t}=e.detail,i=this._state?.master_entity_id;i&&this._call("switch",t?"turn_on":"turn_off",{entity_id:i})},this._closeDialogs=()=>{this._editing=null,this._creatingDay=null,this._duplicateSeed=null,this._defaultsOpen=!1,this._simulateOpen=!1,this._dialogError=null,this._runNowResult=null,this._cloneSource=null,this._cloneLanded=null,this._cloneFailed=null},this._onRuleOpen=e=>{this._editing=e.detail.rule,this._creatingDay=null,this._duplicateSeed=null,this._dialogError=null,this._runNowResult=null},this._onRuleToggleEnabled=e=>{const{rule:t}=e.detail;this._toggleRuleEnabled(t)},this._onRuleAdd=e=>{this._creatingDay=e.detail.day,this._editing=null,this._duplicateSeed=null,this._dialogError=null,this._runNowResult=null},this._onSave=async e=>{const{form:t,rule:i}=e.detail;(null===i?await this._send({type:"shabbat_scheduler/rules/create",rule:Se(t,this._profile)}):await this._saveChanges(t,i))&&this._closeDialogs()},this._onDelete=async e=>{const{rule:t}=e.detail;await this._send({type:"shabbat_scheduler/rules/delete",rule_id:t.id})&&this._closeDialogs()},this._onDuplicate=e=>{const{form:t}=e.detail;this._editing=null,this._creatingDay=t.day,this._duplicateSeed=t,this._dialogError=null},this._onDefaultsSave=async e=>{const{defaults:t}=e.detail;await this._send({type:"shabbat_scheduler/defaults/update",defaults:t})&&this._closeDialogs()},this._onRunNow=async e=>{const{rule:t,simulate:i}=e.detail;try{const e=await this._hass.callWS({type:"shabbat_scheduler/rules/run_now",rule_id:t.id,simulate:i});this._runNowResult={ruleId:t.id,results:e.results,at:(new Date).toISOString()}}catch(e){const t=e;this._dialogError=t?.message??String(e)}},this._onCloneOpen=e=>{this._cloneSource=e.detail,this._cloneLanded=null,this._cloneFailed=null,this._dialogError=null},this._onCloneConfirm=async e=>{const t=e.detail,i=this._cloneTargetDays(t),n=[],r=[];let o=!1;for(const{day:e,ruleIds:s}of i){if(o){r.push(...s);continue}const i=await this._cloneRules(s,t.targetProfile,e,t.mode);n.push(...i.landed),null!==i.error&&(r.push(...i.failed),o=!0)}this._cloneLanded=n,this._cloneFailed=r,0===r.length&&null===this._dialogError&&(this._cloneSource=null)}}setConfig(e){this._config=e??{}}getCardSize(){return 3+this._groups.reduce((e,t)=>e+t.rules.length,0)}static getStubConfig(){return{type:"custom:shabbat-scheduler-card"}}set hass(e){const t=this._language,i=this._canWrite;this._hass=e,this._language===t&&this._canWrite===i||this.requestUpdate(),this._ensureSubscribed()}get hass(){return this._hass}_ensureSubscribed(){!this._subscribed&&this._hass&&this.isConnected&&(this._subscribed=!0,this._subscribe())}async _subscribe(){const e=this._generation;try{const t=await this._hass.connection.subscribeMessage(t=>{e===this._generation&&(this._state?.block?.length!==t.block?.length&&(this._selectedProfile=null),this._state=t,this._error=null)},{type:"shabbat_scheduler/subscribe"});if(e!==this._generation||!this.isConnected)return void this._teardown(t);this._unsubscribe=t}catch(t){if(e!==this._generation)return;this._error=function(e){const t=e?.code;if("string"==typeof t)return t===Li;const i=e?.message;return"string"==typeof i&&i.includes(Li)}(t)?"not_set_up":"stale",this._subscribed=!1}}async _teardown(e){if(null!==e)try{await e()}catch{}}connectedCallback(){super.connectedCallback(),this._ensureSubscribed()}disconnectedCallback(){super.disconnectedCallback(),this._generation+=1;const e=this._unsubscribe;this._unsubscribe=null,this._subscribed=!1,this._teardown(e)}get _language(){return this._hass?.locale?.language??"en"}get _canWrite(){return!0===this._hass?.user?.is_admin}get _profile(){return this._selectedProfile??this._state?.block?.length??1}get _groups(){const e=this._state;return null!==e&&Array.isArray(e.rules)?function(e,t){const{block:i}=e,n=t??i?.length??null;if(null===n)return[];const r=me(e,n),o=String(n);return be(n).map(t=>{const s=e.rules.filter(e=>e.profile===n&&e.day===t).sort((e,t)=>e.time.localeCompare(t.time));let a=null;r||null===i||("erev"===t?a={kind:"candle_lighting",at:i.candle_lighting}:t===o&&(a={kind:"havdalah",at:i.havdalah}));const l=r||null===i?null:i.dates[t]??null;return{day:t,date:l,rules:s,marker:a}}).sort((e,t)=>_e(e.day)-_e(t.day))}(e,this._profile):[]}async _call(e,t,i){try{await this._hass.callService(e,t,i)}catch{this._error="command_failed"}}async _send(e){this._busy=!0,this._dialogError=null;try{return await this._hass.callWS(e),!0}catch(e){const t=e;return this._dialogError=t?.message??String(e),!1}finally{this._busy=!1}}async _toggleRuleEnabled(e){try{if(await this._hass.callWS({type:"shabbat_scheduler/rules/update",rule_id:e.id,changes:{enabled:!e.enabled}}),e.id in this._toggleErrors){const t={...this._toggleErrors};delete t[e.id],this._toggleErrors=t}}catch(t){const i=t;this._toggleErrors={...this._toggleErrors,[e.id]:i?.message??String(t)}}}async _saveChanges(e,t){return this._send({type:"shabbat_scheduler/rules/update",rule_id:t.id,changes:Ee(e,t)})}_cloneCreatePayload(e,t,i){return{day:i,profile:t,time:e.time,action:e.action,target:e.target,data:e.data,condition:e.condition,replay:e.replay,name:e.name,icon:e.icon,color:e.color,enabled:e.enabled}}async _cloneRules(e,t,i,n){if("overwrite"===n){const n=(this._state?.rules??[]).filter(e=>e.profile===t&&e.day===i);for(const t of n){if(!await this._send({type:"shabbat_scheduler/rules/delete",rule_id:t.id}))return{landed:[],failed:e,error:this._dialogError??"Could not clear the target day."}}}const r=this._state?.rules??[],o=[];for(const n of e){const s=r.find(e=>e.id===n);if(void 0===s)continue;if(!await this._send({type:"shabbat_scheduler/rules/create",rule:this._cloneCreatePayload(s,t,i)}))return{landed:o,failed:e.slice(o.length),error:this._dialogError};o.push(n)}return{landed:o,failed:[],error:null}}_cloneTargetDays(e){if("day"===e.sourceScope)return[{day:e.targetDay,ruleIds:e.sourceRuleIds}];const t=new Set(["erev"]);for(let i=1;i<=e.targetProfile;i+=1)t.add(String(i));const i=this._state?.rules??[],n=new Map;for(const r of e.sourceRuleIds){const e=i.find(e=>e.id===r);e&&t.has(e.day)&&n.set(e.day,[...n.get(e.day)??[],r])}return[...n.entries()].map(([e,t])=>({day:e,ruleIds:t}))}render(){const e=this._error;if("not_set_up"===e)return B`
        <ha-card>
          <div class="message">${ge(this._language,"not_set_up")}</div>
        </ha-card>
      `;if(null===this._state)return B`
        <ha-card>
          <div class="message">
            ${null===e?"…":ge(this._language,e)}
          </div>
        </ha-card>
      `;const t=this._groups,i=t.flatMap(e=>e.rules.map(e=>e.id));return B`
      <ha-card
        @rule-open=${this._onRuleOpen}
        @rule-toggle-enabled=${this._onRuleToggleEnabled}
        @simulate-open=${()=>{this._simulateOpen=!0}}
        @clone-open=${this._onCloneOpen}
      >
        ${this._config.title?B`<div class="title">${this._config.title}</div>`:q}
        ${null!==e?B`<div class="message notice">${ge(this._language,e)}</div>`:q}
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
        ${me(this._state,this._profile)?B`<div class="preview">${ge(this._language,"preview_banner")}</div>`:q}
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
              @dialog-save=${this._onDefaultsSave}
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
              .busy=${this._busy}
              .error=${this._dialogError}
              .landed=${this._cloneLanded}
              .failed=${this._cloneFailed}
              .language=${this._language}
              @dialog-clone-confirm=${this._onCloneConfirm}
              @dialog-close=${()=>{this._cloneSource=null}}
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
  `,e([pe()],Ui.prototype,"_state",void 0),e([pe()],Ui.prototype,"_error",void 0),e([he({attribute:!1})],Ui.prototype,"_config",void 0),e([pe()],Ui.prototype,"_selectedProfile",void 0),e([pe()],Ui.prototype,"_editing",void 0),e([pe()],Ui.prototype,"_creatingDay",void 0),e([pe()],Ui.prototype,"_defaultsOpen",void 0),e([pe()],Ui.prototype,"_simulateOpen",void 0),e([pe()],Ui.prototype,"_dialogError",void 0),e([pe()],Ui.prototype,"_toggleErrors",void 0),e([pe()],Ui.prototype,"_busy",void 0),e([pe()],Ui.prototype,"_duplicateSeed",void 0),e([pe()],Ui.prototype,"_runNowResult",void 0),e([pe()],Ui.prototype,"_cloneSource",void 0),e([pe()],Ui.prototype,"_cloneLanded",void 0),e([pe()],Ui.prototype,"_cloneFailed",void 0),Ui=e([ce("shabbat-scheduler-card")],Ui),window.customCards=window.customCards??[],window.customCards.push({type:"shabbat-scheduler-card",name:"Shabbat Scheduler",description:"The coming Shabbat or Chag as a timeline."}),console.info("shabbat-scheduler-card 0.5.0");export{Ui as ShabbatSchedulerCard};
