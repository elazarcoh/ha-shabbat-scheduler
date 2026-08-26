function t(t,e,i,n){var r,o=arguments.length,s=o<3?e:null===n?n=Object.getOwnPropertyDescriptor(e,i):n;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)s=Reflect.decorate(t,e,i,n);else for(var a=t.length-1;a>=0;a--)(r=t[a])&&(s=(o<3?r(s):o>3?r(e,i,s):r(e,i))||s);return o>3&&s&&Object.defineProperty(e,i,s),s}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,i=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,n=Symbol(),r=new WeakMap;let o=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==n)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(i&&void 0===t){const i=void 0!==e&&1===e.length;i&&(t=r.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&r.set(e,t))}return t}toString(){return this.cssText}};const s=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,i,n)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+t[n+1],t[0]);return new o(i,t,n)},a=i?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const i of t.cssRules)e+=i.cssText;return(t=>new o("string"==typeof t?t:t+"",void 0,n))(e)})(t):t,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:u,getOwnPropertySymbols:h,getPrototypeOf:p}=Object,f=globalThis,g=f.trustedTypes,b=g?g.emptyScript:"",v=f.reactiveElementPolyfillSupport,m=(t,e)=>t,_={toAttribute(t,e){switch(e){case Boolean:t=t?b:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let i=t;switch(e){case Boolean:i=null!==t;break;case Number:i=null===t?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t)}catch(t){i=null}}return i}},y=(t,e)=>!l(t,e),$={attribute:!0,type:String,converter:_,reflect:!1,useDefault:!1,hasChanged:y};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),f.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=$){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const i=Symbol(),n=this.getPropertyDescriptor(t,i,e);void 0!==n&&c(this.prototype,t,n)}}static getPropertyDescriptor(t,e,i){const{get:n,set:r}=d(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:n,set(e){const o=n?.call(this);r?.call(this,e),this.requestUpdate(t,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??$}static _$Ei(){if(this.hasOwnProperty(m("elementProperties")))return;const t=p(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(m("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(m("properties"))){const t=this.properties,e=[...u(t),...h(t)];for(const i of e)this.createProperty(i,t[i])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,i]of e)this.elementProperties.set(t,i)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const i=this._$Eu(t,e);void 0!==i&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const i=new Set(t.flat(1/0).reverse());for(const t of i)e.unshift(a(t))}else void 0!==t&&e.push(a(t));return e}static _$Eu(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,n)=>{if(i)t.adoptedStyleSheets=n.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const i of n){const n=document.createElement("style"),r=e.litNonce;void 0!==r&&n.setAttribute("nonce",r),n.textContent=i.cssText,t.appendChild(n)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){const i=this.constructor.elementProperties.get(t),n=this.constructor._$Eu(t,i);if(void 0!==n&&!0===i.reflect){const r=(void 0!==i.converter?.toAttribute?i.converter:_).toAttribute(e,i.type);this._$Em=t,null==r?this.removeAttribute(n):this.setAttribute(n,r),this._$Em=null}}_$AK(t,e){const i=this.constructor,n=i._$Eh.get(t);if(void 0!==n&&this._$Em!==n){const t=i.getPropertyOptions(n),r="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:_;this._$Em=n;const o=r.fromAttribute(e,t.type);this[n]=o??this._$Ej?.get(n)??o,this._$Em=null}}requestUpdate(t,e,i,n=!1,r){if(void 0!==t){const o=this.constructor;if(!1===n&&(r=this[t]),i??=o.getPropertyOptions(t),!((i.hasChanged??y)(r,e)||i.useDefault&&i.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,i))))return;this.C(t,e,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:n,wrapped:r},o){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),!0!==r||void 0!==o)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),!0===n&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,i]of t){const{wrapped:t}=i,n=this[e];!0!==t||this._$AL.has(e)||void 0===n||this.C(e,void 0,i,n)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[m("elementProperties")]=new Map,w[m("finalized")]=new Map,v?.({ReactiveElement:w}),(f.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x=globalThis,A=t=>t,k=x.trustedTypes,E=k?k.createPolicy("lit-html",{createHTML:t=>t}):void 0,C="$lit$",S=`lit$${Math.random().toFixed(9).slice(2)}$`,O="?"+S,I=`<${O}>`,T=document,j=()=>T.createComment(""),N=t=>null===t||"object"!=typeof t&&"function"!=typeof t,M=Array.isArray,R="[ \t\n\f\r]",P=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,D=/-->/g,U=/>/g,W=RegExp(`>|${R}(?:([^\\s"'>=/]+)(${R}*=${R}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),z=/'/g,L=/"/g,F=/^(?:script|style|textarea|title)$/i,B=(t=>(e,...i)=>({_$litType$:t,strings:e,values:i}))(1),H=Symbol.for("lit-noChange"),q=Symbol.for("lit-nothing"),Y=new WeakMap,V=T.createTreeWalker(T,129);function K(t,e){if(!M(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==E?E.createHTML(e):e}const G=(t,e)=>{const i=t.length-1,n=[];let r,o=2===e?"<svg>":3===e?"<math>":"",s=P;for(let e=0;e<i;e++){const i=t[e];let a,l,c=-1,d=0;for(;d<i.length&&(s.lastIndex=d,l=s.exec(i),null!==l);)d=s.lastIndex,s===P?"!--"===l[1]?s=D:void 0!==l[1]?s=U:void 0!==l[2]?(F.test(l[2])&&(r=RegExp("</"+l[2],"g")),s=W):void 0!==l[3]&&(s=W):s===W?">"===l[0]?(s=r??P,c=-1):void 0===l[1]?c=-2:(c=s.lastIndex-l[2].length,a=l[1],s=void 0===l[3]?W:'"'===l[3]?L:z):s===L||s===z?s=W:s===D||s===U?s=P:(s=W,r=void 0);const u=s===W&&t[e+1].startsWith("/>")?" ":"";o+=s===P?i+I:c>=0?(n.push(a),i.slice(0,c)+C+i.slice(c)+S+u):i+S+(-2===c?e:u)}return[K(t,o+(t[i]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),n]};class J{constructor({strings:t,_$litType$:e},i){let n;this.parts=[];let r=0,o=0;const s=t.length-1,a=this.parts,[l,c]=G(t,e);if(this.el=J.createElement(l,i),V.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(n=V.nextNode())&&a.length<s;){if(1===n.nodeType){if(n.hasAttributes())for(const t of n.getAttributeNames())if(t.endsWith(C)){const e=c[o++],i=n.getAttribute(t).split(S),s=/([.?@])?(.*)/.exec(e);a.push({type:1,index:r,name:s[2],strings:i,ctor:"."===s[1]?et:"?"===s[1]?it:"@"===s[1]?nt:tt}),n.removeAttribute(t)}else t.startsWith(S)&&(a.push({type:6,index:r}),n.removeAttribute(t));if(F.test(n.tagName)){const t=n.textContent.split(S),e=t.length-1;if(e>0){n.textContent=k?k.emptyScript:"";for(let i=0;i<e;i++)n.append(t[i],j()),V.nextNode(),a.push({type:2,index:++r});n.append(t[e],j())}}}else if(8===n.nodeType)if(n.data===O)a.push({type:2,index:r});else{let t=-1;for(;-1!==(t=n.data.indexOf(S,t+1));)a.push({type:7,index:r}),t+=S.length-1}r++}}static createElement(t,e){const i=T.createElement("template");return i.innerHTML=t,i}}function Z(t,e,i=t,n){if(e===H)return e;let r=void 0!==n?i._$Co?.[n]:i._$Cl;const o=N(e)?void 0:e._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),void 0===o?r=void 0:(r=new o(t),r._$AT(t,i,n)),void 0!==n?(i._$Co??=[])[n]=r:i._$Cl=r),void 0!==r&&(e=Z(t,r._$AS(t,e.values),r,n)),e}class Q{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:i}=this._$AD,n=(t?.creationScope??T).importNode(e,!0);V.currentNode=n;let r=V.nextNode(),o=0,s=0,a=i[0];for(;void 0!==a;){if(o===a.index){let e;2===a.type?e=new X(r,r.nextSibling,this,t):1===a.type?e=new a.ctor(r,a.name,a.strings,this,t):6===a.type&&(e=new rt(r,this,t)),this._$AV.push(e),a=i[++s]}o!==a?.index&&(r=V.nextNode(),o++)}return V.currentNode=T,n}p(t){let e=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}}class X{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,n){this.type=2,this._$AH=q,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Z(this,t,e),N(t)?t===q||null==t||""===t?(this._$AH!==q&&this._$AR(),this._$AH=q):t!==this._$AH&&t!==H&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>M(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==q&&N(this._$AH)?this._$AA.nextSibling.data=t:this.T(T.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:i}=t,n="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=J.createElement(K(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===n)this._$AH.p(e);else{const t=new Q(n,this),i=t.u(this.options);t.p(e),this.T(i),this._$AH=t}}_$AC(t){let e=Y.get(t.strings);return void 0===e&&Y.set(t.strings,e=new J(t)),e}k(t){M(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let i,n=0;for(const r of t)n===e.length?e.push(i=new X(this.O(j()),this.O(j()),this,this.options)):i=e[n],i._$AI(r),n++;n<e.length&&(this._$AR(i&&i._$AB.nextSibling,n),e.length=n)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=A(t).nextSibling;A(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,n,r){this.type=1,this._$AH=q,this._$AN=void 0,this.element=t,this.name=e,this._$AM=n,this.options=r,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=q}_$AI(t,e=this,i,n){const r=this.strings;let o=!1;if(void 0===r)t=Z(this,t,e,0),o=!N(t)||t!==this._$AH&&t!==H,o&&(this._$AH=t);else{const n=t;let s,a;for(t=r[0],s=0;s<r.length-1;s++)a=Z(this,n[i+s],e,s),a===H&&(a=this._$AH[s]),o||=!N(a)||a!==this._$AH[s],a===q?t=q:t!==q&&(t+=(a??"")+r[s+1]),this._$AH[s]=a}o&&!n&&this.j(t)}j(t){t===q?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===q?void 0:t}}class it extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==q)}}class nt extends tt{constructor(t,e,i,n,r){super(t,e,i,n,r),this.type=5}_$AI(t,e=this){if((t=Z(this,t,e,0)??q)===H)return;const i=this._$AH,n=t===q&&i!==q||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,r=t!==q&&(i===q||n);n&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class rt{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){Z(this,t)}}const ot=x.litHtmlPolyfillSupport;ot?.(J,X),(x.litHtmlVersions??=[]).push("3.3.3");const st=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */let at=class extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,i)=>{const n=i?.renderBefore??e;let r=n._$litPart$;if(void 0===r){const t=i?.renderBefore??null;n._$litPart$=r=new X(e.insertBefore(j(),t),t,void 0,i??{})}return r._$AI(t),r})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return H}};at._$litElement$=!0,at.finalized=!0,st.litElementHydrateSupport?.({LitElement:at});const lt=st.litElementPolyfillSupport;lt?.({LitElement:at}),(st.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ct=t=>(e,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},dt={attribute:!0,type:String,converter:_,reflect:!1,hasChanged:y},ut=(t=dt,e,i)=>{const{kind:n,metadata:r}=i;let o=globalThis.litPropertyMetadata.get(r);if(void 0===o&&globalThis.litPropertyMetadata.set(r,o=new Map),"setter"===n&&((t=Object.create(t)).wrapped=!0),o.set(i.name,t),"accessor"===n){const{name:n}=i;return{set(i){const r=e.get.call(this);e.set.call(this,i),this.requestUpdate(n,r,t,!0,i)},init(e){return void 0!==e&&this.C(n,void 0,t,e),e}}}if("setter"===n){const{name:n}=i;return function(i){const r=this[n];e.call(this,i),this.requestUpdate(n,r,t,!0,i)}}throw Error("Unsupported decorator location: "+n)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ht(t){return(e,i)=>"object"==typeof i?ut(t,e,i):((t,e,i)=>{const n=e.hasOwnProperty(i);return e.constructor.createProperty(i,t),n?Object.getOwnPropertyDescriptor(e,i):void 0})(t,e,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pt(t){return ht({...t,state:!0,attribute:!1})}const ft={en:{erev:"Erev",day:"Day",candle_lighting:"Candle lighting",havdalah:"Havdalah",master:"Shabbat Scheduler",dry_run:"Dry run",no_block:"No upcoming Shabbat could be derived from the Jewish Calendar sensors.",not_set_up:"Shabbat Scheduler is not configured.",stale:"Connection lost — showing the last known state.",command_failed:"That did not go through. Nothing was changed.",no_rules:"No rules for this block.",disabled_rule:"disabled",conflict_prefix:"Conflict",edit_rule:"Edit rule",add_rule:"Add rule",time:"Time",name:"Name",enabled:"Enabled",advanced:"Advanced",icon:"Icon",colour:"Colour",save:"Save",cancel:"Cancel",delete_rule:"Delete",duplicate:"Duplicate",read_only:"You do not have permission to change the schedule.",will_conflict:"This overlaps another rule. You can still save it — nothing is resolved for you.",defaults_title:"Shared defaults",defaults_help:"Rules inherit these unless they set their own.",target:"Target",data:"Data",migration_error:"This rule could not be converted from the old format and will not fire:",preview_banner:"Preview — not the coming Shabbat. Dates are not shown because this block is not scheduled.",inherits_target_from_defaults:"Inherited from the shared defaults:",target_none:"No target — this rule will not reach anything.",replay_after_restart:"Replay after a restart",replay_within_label:"Only if less than",replay_help:"Off by default: after a restart, nothing that already passed is re-run.",conditions:"Conditions",conditions_help:"All conditions must pass, or the rule does not run and says why.",add_condition:"Add condition",remove_condition:"Remove",condition_unparseable:"Not valid YAML — this condition is not being saved.",condition_not_a_mapping:"A condition must be a mapping, like `condition: state`.",outcome_called:"Fired",outcome_would_call:"Would have fired [dry run]",outcome_failed:"Did not run — failed",outcome_blocked:"Did not run — blocked",outcome_skipped_stale:"Did not run — skipped as stale",outcome_skipped_no_replay:"Did not run — was due after a restart, replay is off",outcome_unknown:"Finished with no reported outcome",outcome_no_such_entity:"no such entity: ",outcome_reached_nothing:"reached no entity that exists"},he:{erev:"ערב",day:"יום",candle_lighting:"הדלקת נרות",havdalah:"הבדלה",master:"שעון שבת",dry_run:"הרצה יבשה",no_block:"לא ניתן לגזור שבת קרובה מחיישני לוח השנה העברי.",not_set_up:"שעון שבת אינו מוגדר.",stale:"החיבור אבד — מוצג המצב האחרון הידוע.",command_failed:"הפעולה לא בוצעה. שום דבר לא השתנה.",no_rules:"אין כללים לבלוק הזה.",disabled_rule:"מושבת",conflict_prefix:"התנגשות",edit_rule:"עריכת כלל",add_rule:"הוספת כלל",time:"שעה",name:"שם",enabled:"מופעל",advanced:"מתקדם",icon:"סמל",colour:"צבע",save:"שמירה",cancel:"ביטול",delete_rule:"מחיקה",duplicate:"שכפול",read_only:"אין לך הרשאה לשנות את הלוח.",will_conflict:"הכלל חופף לכלל אחר. אפשר לשמור בכל זאת — שום דבר לא ייפתר עבורך.",defaults_title:"ברירות מחדל משותפות",defaults_help:"כללים יורשים אותן אלא אם הגדירו משלהם.",target:"יעד",data:"נתונים",migration_error:"לא ניתן להמיר את הכלל הזה מהפורמט הישן והוא לא יופעל:",preview_banner:"תצוגה מקדימה — לא השבת הקרובה. התאריכים אינם מוצגים כי הבלוק הזה אינו מתוכנן.",inherits_target_from_defaults:"נורש מברירת המחדל המשותפת:",target_none:"ללא יעד — הכלל לא יפעל על שום דבר.",replay_after_restart:"הפעלה חוזרת לאחר אתחול",replay_within_label:"רק אם עברו פחות מ־",replay_help:"כברירת מחדל כבוי: לאחר אתחול, מה שכבר עבר לא יופעל שוב.",conditions:"תנאים",conditions_help:"כל התנאים חייבים להתקיים, אחרת הכלל לא ירוץ ויציין זאת.",add_condition:"הוספת תנאי",remove_condition:"הסרה",condition_unparseable:"YAML לא תקין — התנאי הזה לא נשמר.",condition_not_a_mapping:"תנאי חייב להיות מפה, כמו `condition: state`.",outcome_called:"הופעל",outcome_would_call:"היה מופעל [הרצה יבשה]",outcome_failed:"לא רץ — נכשל",outcome_blocked:"לא רץ — נחסם",outcome_skipped_stale:"לא רץ — דולג כמיושן",outcome_skipped_no_replay:"לא רץ — היה אמור לרוץ לאחר אתחול, הפעלה חוזרת כבויה",outcome_unknown:"הסתיים ללא תוצאה מדווחת",outcome_no_such_entity:"אין ישות כזו: ",outcome_reached_nothing:"לא הגיע לאף ישות קיימת"}};function gt(t,e){return("he"===t?ft.he:ft.en)[e]}function bt(t){return"erev"===t?-1:Number(t)}function vt(t){const e=["erev"];for(let i=1;i<=t;i+=1)e.push(String(i));return e}function mt(t){return function(t){return vt(t.length)}(t).map(e=>t.dates[e]).filter(t=>void 0!==t)}function _t(t,e){return null===t.block||t.block.length!==e}function yt(t){const e=[];for(const i of Object.values(t))Array.isArray(i)?e.push(...i.map(String)):null!=i&&e.push(String(i));return e.join(", ")}function $t(t,e){if("conflict"===t.kind&&void 0!==t.targets&&t.targets.length>0&&void 0!==t.time){const i=[gt(e,"conflict_prefix"),t.targets.join(", ")];return void 0!==t.day&&i.push(function(t,e){return"erev"===t?gt(e,"erev"):`${gt(e,"day")} ${t}`}(t.day,e)),i.push(t.time),i.join(" · ")}return t.message??""}const wt={called:"outcome_called",would_call:"outcome_would_call",failed:"outcome_failed",blocked:"outcome_blocked",skipped_stale:"outcome_skipped_stale",skipped_no_replay:"outcome_skipped_no_replay"};const xt=["day","time","action","target","data","condition","replay","name","icon","color","enabled"];function At(t,e){return{...t,profile:e}}function kt(t,e){const i={};for(const n of xt){const r=t[n],o=e[n];JSON.stringify(r)!==JSON.stringify(o)&&(i[n]=r)}return i}let Et=class extends at{constructor(){super(...arguments),this.hass=null,this.block=null,this.enabled=!1,this.dryRun=!1,this.canWrite=!1,this.masterEntityId=null,this.language="en",this.selectedProfile=1,this._onMasterChanged=t=>{this.dispatchEvent(new CustomEvent("shabbat-master-toggle",{detail:{enabled:Boolean(t.detail?.value)}}))}}_dates(){return null===this.block?"":mt(this.block).join(" → ")}_toggleDryRun(){this.dispatchEvent(new CustomEvent("shabbat-dry-run-toggle",{detail:{dryRun:!this.dryRun}}))}render(){return B`
      <div class="header">
        <div class="label">
          ${null===this.block?B`<span class="none">${gt(this.language,"no_block")}</span>`:B`
                <span>${gt(this.language,"day")} ×${this.block.length}</span>
                <span class="dates">${this._dates()}</span>
              `}
        </div>
        <div class="chips">
          ${[1,2,3].map(t=>B`
              <button
                class="chip ${this.selectedProfile===t?"active":""}"
                @click=${()=>this.dispatchEvent(new CustomEvent("profile-selected",{detail:{profile:t}}))}
              >
                ${t}d
              </button>
            `)}
        </div>
        ${this.canWrite?B`<button
              class="gear"
              @click=${()=>this.dispatchEvent(new CustomEvent("defaults-open"))}
            >
              ⚙
            </button>`:q}
        <div class="master-wrap">
          <span class="master-label">${gt(this.language,"master")}</span>
          <ha-selector
            class="master"
            .hass=${this.hass}
            .selector=${{boolean:{}}}
            .value=${this.enabled}
            .disabled=${!this.canWrite||null===this.masterEntityId}
            @value-changed=${this._onMasterChanged}
          ></ha-selector>
        </div>
        <button
          class="dry-run ${this.dryRun?"active":""}"
          ?disabled=${!this.canWrite}
          @click=${this._toggleDryRun}
        >
          ${gt(this.language,"dry_run")}
        </button>
      </div>
    `}};Et.styles=s`
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
    .gear { border: none; background: none; cursor: pointer; font-size: 1.1em; }
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
  `,t([ht({attribute:!1})],Et.prototype,"hass",void 0),t([ht({attribute:!1})],Et.prototype,"block",void 0),t([ht({type:Boolean})],Et.prototype,"enabled",void 0),t([ht({type:Boolean})],Et.prototype,"dryRun",void 0),t([ht({type:Boolean})],Et.prototype,"canWrite",void 0),t([ht()],Et.prototype,"masterEntityId",void 0),t([ht()],Et.prototype,"language",void 0),t([ht({type:Number})],Et.prototype,"selectedProfile",void 0),Et=t([ct("shabbat-block-header")],Et);let Ct=class extends at{constructor(){super(...arguments),this.hass=null,this.defaults={},this.warnings=[],this.canWrite=!1,this.toggleError=null,this.language="en"}_open(){this.dispatchEvent(new CustomEvent("rule-open",{detail:{rule:this.rule},bubbles:!0,composed:!0}))}render(){const t=(e=this.rule.id,this.warnings.filter(t=>t.rule_ids?.includes(e)));var e;const i=this.rule.name,n=this.rule.last_outcome??null,r=null===n?"":function(t,e){const i=new Date(t);return Number.isNaN(i.getTime())?"":i.toLocaleString("he"===e?"he-IL":"en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}(n.at,this.language);return B`
      <div
        class="row ${this.rule.enabled?"":"disabled"}"
        tabindex="0"
        role="button"
        @click=${()=>this._open()}
        @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._open())}}
      >
        ${this.canWrite?B`<ha-selector
              class="row-toggle"
              .hass=${this.hass}
              .selector=${{boolean:{}}}
              .value=${this.rule.enabled}
              @click=${t=>t.stopPropagation()}
              @keydown=${t=>t.stopPropagation()}
              @value-changed=${()=>{this.dispatchEvent(new CustomEvent("rule-toggle-enabled",{detail:{rule:this.rule},bubbles:!0,composed:!0}))}}
            ></ha-selector>`:q}
        <span class="dot" style="background:${o=this.rule,o.color??"var(--secondary-text-color, #888)"}"></span>
        <span class="time">${this.rule.time.slice(0,5)}</span>
        <div class="body">
          ${i?B`<div class="title">${i}</div>`:q}
          <div class="brief">${function(t,e){const i=Object.keys(t.target).length?t.target:e.target??{},n={...e.data??{},...t.data},r=[t.action,yt(i)];for(const t of Object.values(n))null!=t&&r.push(String(t));return r.filter(t=>""!==t).join(" · ")}(this.rule,this.defaults)}</div>
          ${null!==this.toggleError?B`<div class="row-error">${this.toggleError}</div>`:q}
          ${null!==n?B`<div class="last-outcome ${function(t){return"failed"===t.outcome||"blocked"===t.outcome||"skipped_stale"===t.outcome||(t.unknown_targets??[]).length>0||!0===t.no_live_targets||!(t.outcome in wt)}(n)?"bad":""}">
                <span>${function(t,e){let i=gt(e,wt[t.outcome]??"outcome_unknown");t.detail&&(i=`${i}: ${t.detail}`);const n=t.unknown_targets??[];return n.length>0&&!i.includes("no such entity: ")&&(i=`${i} — ${gt(e,"outcome_no_such_entity")}${n.join(", ")}`),!0===t.no_live_targets&&(i=`${i} — ${gt(e,"outcome_reached_nothing")}`),i}(n,this.language)}</span>
                ${r?B`<span class="last-outcome-at">${r}</span>`:q}
              </div>`:q}
          ${t.length?B`<div class="conflict-detail">
                ${t.map(t=>B`<div>${$t(t,this.language)}</div>`)}
              </div>`:q}
        </div>
        ${this.rule.enabled?q:B`<span class="tag">${gt(this.language,"disabled_rule")}</span>`}
        ${t.length?B`<span
              class="conflict"
              role="img"
              aria-label=${t.map(t=>$t(t,this.language)).join("; ")}
              title=${$t(t[0],this.language)}
              >⚠</span
            >`:q}
      </div>
    `;var o}};Ct.styles=s`
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
  `,t([ht({attribute:!1})],Ct.prototype,"hass",void 0),t([ht({attribute:!1})],Ct.prototype,"rule",void 0),t([ht({attribute:!1})],Ct.prototype,"defaults",void 0),t([ht({attribute:!1})],Ct.prototype,"warnings",void 0),t([ht({type:Boolean})],Ct.prototype,"canWrite",void 0),t([ht()],Ct.prototype,"toggleError",void 0),t([ht()],Ct.prototype,"language",void 0),Ct=t([ct("shabbat-rule-row")],Ct);let St=class extends at{constructor(){super(...arguments),this.hass=null,this.defaults={},this.warnings=[],this.language="en",this.canWrite=!1,this.toggleErrors={}}label(){const{day:t}=this.group;return"erev"===t?gt(this.language,"erev"):`${gt(this.language,"day")} ${t}`}render(){const{marker:t,rules:e}=this.group;return B`
      <div class="day-group">
        <div class="heading">
          <span>${this.label()}</span>
          <span class="date">${this.group.date??""}</span>
        </div>
        ${e.length?e.map(t=>B`
                <shabbat-rule-row
                  .hass=${this.hass}
                  .rule=${t}
                  .defaults=${this.defaults}
                  .warnings=${this.warnings}
                  .language=${this.language}
                  .canWrite=${this.canWrite}
                  .toggleError=${this.toggleErrors[t.id]??null}
                ></shabbat-rule-row>
              `):B`<div class="empty">${gt(this.language,"no_rules")}</div>`}
        ${this.canWrite?B`<button
              class="add"
              @click=${()=>this.dispatchEvent(new CustomEvent("rule-add",{detail:{day:this.group.day}}))}
            >
              + ${gt(this.language,"add_rule")}
            </button>`:q}
        ${t?B`
              <div class="marker">
                <span>${"havdalah"===t.kind?"✨":"🕯️"}</span>
                <span>${gt(this.language,t.kind)}</span>
                <span>${function(t){const e=/T(\d{2}:\d{2})/.exec(t);return e?e[1]:t}(t.at)}</span>
              </div>
            `:q}
      </div>
    `}};St.styles=s`
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
  `,t([ht({attribute:!1})],St.prototype,"hass",void 0),t([ht({attribute:!1})],St.prototype,"group",void 0),t([ht({attribute:!1})],St.prototype,"defaults",void 0),t([ht({attribute:!1})],St.prototype,"warnings",void 0),t([ht()],St.prototype,"language",void 0),t([ht({type:Boolean})],St.prototype,"canWrite",void 0),t([ht({attribute:!1})],St.prototype,"toggleErrors",void 0),St=t([ct("shabbat-day-group")],St);let Ot=class extends at{constructor(){super(...arguments),this.warnings=[],this.displayedRuleIds=[],this.language="en"}render(){const t=function(t,e){const i=new Set(e);return t.filter(t=>!t.rule_ids?.some(t=>i.has(t)))}(this.warnings,this.displayedRuleIds);return t.length?B`
      <div class="banner">
        ${t.map(t=>B`<span>${$t(t,this.language)}</span>`)}
      </div>
    `:q}};
/*! js-yaml 4.1.0 https://github.com/nodeca/js-yaml @license MIT */
function It(t){return null==t}Ot.styles=s`
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
  `,t([ht({attribute:!1})],Ot.prototype,"warnings",void 0),t([ht({attribute:!1})],Ot.prototype,"displayedRuleIds",void 0),t([ht()],Ot.prototype,"language",void 0),Ot=t([ct("shabbat-warnings")],Ot);var Tt={isNothing:It,isObject:function(t){return"object"==typeof t&&null!==t},toArray:function(t){return Array.isArray(t)?t:It(t)?[]:[t]},repeat:function(t,e){var i,n="";for(i=0;i<e;i+=1)n+=t;return n},isNegativeZero:function(t){return 0===t&&Number.NEGATIVE_INFINITY===1/t},extend:function(t,e){var i,n,r,o;if(e)for(i=0,n=(o=Object.keys(e)).length;i<n;i+=1)t[r=o[i]]=e[r];return t}};function jt(t,e){var i="",n=t.reason||"(unknown reason)";return t.mark?(t.mark.name&&(i+='in "'+t.mark.name+'" '),i+="("+(t.mark.line+1)+":"+(t.mark.column+1)+")",!e&&t.mark.snippet&&(i+="\n\n"+t.mark.snippet),n+" "+i):n}function Nt(t,e){Error.call(this),this.name="YAMLException",this.reason=t,this.mark=e,this.message=jt(this,!1),Error.captureStackTrace?Error.captureStackTrace(this,this.constructor):this.stack=(new Error).stack||""}Nt.prototype=Object.create(Error.prototype),Nt.prototype.constructor=Nt,Nt.prototype.toString=function(t){return this.name+": "+jt(this,t)};var Mt=Nt;function Rt(t,e,i,n,r){var o="",s="",a=Math.floor(r/2)-1;return n-e>a&&(e=n-a+(o=" ... ").length),i-n>a&&(i=n+a-(s=" ...").length),{str:o+t.slice(e,i).replace(/\t/g,"→")+s,pos:n-e+o.length}}function Pt(t,e){return Tt.repeat(" ",e-t.length)+t}var Dt=function(t,e){if(e=Object.create(e||null),!t.buffer)return null;e.maxLength||(e.maxLength=79),"number"!=typeof e.indent&&(e.indent=1),"number"!=typeof e.linesBefore&&(e.linesBefore=3),"number"!=typeof e.linesAfter&&(e.linesAfter=2);for(var i,n=/\r?\n|\r|\0/g,r=[0],o=[],s=-1;i=n.exec(t.buffer);)o.push(i.index),r.push(i.index+i[0].length),t.position<=i.index&&s<0&&(s=r.length-2);s<0&&(s=r.length-1);var a,l,c="",d=Math.min(t.line+e.linesAfter,o.length).toString().length,u=e.maxLength-(e.indent+d+3);for(a=1;a<=e.linesBefore&&!(s-a<0);a++)l=Rt(t.buffer,r[s-a],o[s-a],t.position-(r[s]-r[s-a]),u),c=Tt.repeat(" ",e.indent)+Pt((t.line-a+1).toString(),d)+" | "+l.str+"\n"+c;for(l=Rt(t.buffer,r[s],o[s],t.position,u),c+=Tt.repeat(" ",e.indent)+Pt((t.line+1).toString(),d)+" | "+l.str+"\n",c+=Tt.repeat("-",e.indent+d+3+l.pos)+"^\n",a=1;a<=e.linesAfter&&!(s+a>=o.length);a++)l=Rt(t.buffer,r[s+a],o[s+a],t.position-(r[s]-r[s+a]),u),c+=Tt.repeat(" ",e.indent)+Pt((t.line+a+1).toString(),d)+" | "+l.str+"\n";return c.replace(/\n$/,"")},Ut=["kind","multi","resolve","construct","instanceOf","predicate","represent","representName","defaultStyle","styleAliases"],Wt=["scalar","sequence","mapping"];var zt=function(t,e){if(e=e||{},Object.keys(e).forEach(function(e){if(-1===Ut.indexOf(e))throw new Mt('Unknown option "'+e+'" is met in definition of "'+t+'" YAML type.')}),this.options=e,this.tag=t,this.kind=e.kind||null,this.resolve=e.resolve||function(){return!0},this.construct=e.construct||function(t){return t},this.instanceOf=e.instanceOf||null,this.predicate=e.predicate||null,this.represent=e.represent||null,this.representName=e.representName||null,this.defaultStyle=e.defaultStyle||null,this.multi=e.multi||!1,this.styleAliases=function(t){var e={};return null!==t&&Object.keys(t).forEach(function(i){t[i].forEach(function(t){e[String(t)]=i})}),e}(e.styleAliases||null),-1===Wt.indexOf(this.kind))throw new Mt('Unknown kind "'+this.kind+'" is specified for "'+t+'" YAML type.')};function Lt(t,e){var i=[];return t[e].forEach(function(t){var e=i.length;i.forEach(function(i,n){i.tag===t.tag&&i.kind===t.kind&&i.multi===t.multi&&(e=n)}),i[e]=t}),i}function Ft(t){return this.extend(t)}Ft.prototype.extend=function(t){var e=[],i=[];if(t instanceof zt)i.push(t);else if(Array.isArray(t))i=i.concat(t);else{if(!t||!Array.isArray(t.implicit)&&!Array.isArray(t.explicit))throw new Mt("Schema.extend argument should be a Type, [ Type ], or a schema definition ({ implicit: [...], explicit: [...] })");t.implicit&&(e=e.concat(t.implicit)),t.explicit&&(i=i.concat(t.explicit))}e.forEach(function(t){if(!(t instanceof zt))throw new Mt("Specified list of YAML types (or a single Type object) contains a non-Type object.");if(t.loadKind&&"scalar"!==t.loadKind)throw new Mt("There is a non-scalar type in the implicit list of a schema. Implicit resolving of such types is not supported.");if(t.multi)throw new Mt("There is a multi type in the implicit list of a schema. Multi tags can only be listed as explicit.")}),i.forEach(function(t){if(!(t instanceof zt))throw new Mt("Specified list of YAML types (or a single Type object) contains a non-Type object.")});var n=Object.create(Ft.prototype);return n.implicit=(this.implicit||[]).concat(e),n.explicit=(this.explicit||[]).concat(i),n.compiledImplicit=Lt(n,"implicit"),n.compiledExplicit=Lt(n,"explicit"),n.compiledTypeMap=function(){var t,e,i={scalar:{},sequence:{},mapping:{},fallback:{},multi:{scalar:[],sequence:[],mapping:[],fallback:[]}};function n(t){t.multi?(i.multi[t.kind].push(t),i.multi.fallback.push(t)):i[t.kind][t.tag]=i.fallback[t.tag]=t}for(t=0,e=arguments.length;t<e;t+=1)arguments[t].forEach(n);return i}(n.compiledImplicit,n.compiledExplicit),n};var Bt=new Ft({explicit:[new zt("tag:yaml.org,2002:str",{kind:"scalar",construct:function(t){return null!==t?t:""}}),new zt("tag:yaml.org,2002:seq",{kind:"sequence",construct:function(t){return null!==t?t:[]}}),new zt("tag:yaml.org,2002:map",{kind:"mapping",construct:function(t){return null!==t?t:{}}})]});var Ht=new zt("tag:yaml.org,2002:null",{kind:"scalar",resolve:function(t){if(null===t)return!0;var e=t.length;return 1===e&&"~"===t||4===e&&("null"===t||"Null"===t||"NULL"===t)},construct:function(){return null},predicate:function(t){return null===t},represent:{canonical:function(){return"~"},lowercase:function(){return"null"},uppercase:function(){return"NULL"},camelcase:function(){return"Null"},empty:function(){return""}},defaultStyle:"lowercase"});var qt=new zt("tag:yaml.org,2002:bool",{kind:"scalar",resolve:function(t){if(null===t)return!1;var e=t.length;return 4===e&&("true"===t||"True"===t||"TRUE"===t)||5===e&&("false"===t||"False"===t||"FALSE"===t)},construct:function(t){return"true"===t||"True"===t||"TRUE"===t},predicate:function(t){return"[object Boolean]"===Object.prototype.toString.call(t)},represent:{lowercase:function(t){return t?"true":"false"},uppercase:function(t){return t?"TRUE":"FALSE"},camelcase:function(t){return t?"True":"False"}},defaultStyle:"lowercase"});function Yt(t){return 48<=t&&t<=57||65<=t&&t<=70||97<=t&&t<=102}function Vt(t){return 48<=t&&t<=55}function Kt(t){return 48<=t&&t<=57}var Gt=new zt("tag:yaml.org,2002:int",{kind:"scalar",resolve:function(t){if(null===t)return!1;var e,i=t.length,n=0,r=!1;if(!i)return!1;if("-"!==(e=t[n])&&"+"!==e||(e=t[++n]),"0"===e){if(n+1===i)return!0;if("b"===(e=t[++n])){for(n++;n<i;n++)if("_"!==(e=t[n])){if("0"!==e&&"1"!==e)return!1;r=!0}return r&&"_"!==e}if("x"===e){for(n++;n<i;n++)if("_"!==(e=t[n])){if(!Yt(t.charCodeAt(n)))return!1;r=!0}return r&&"_"!==e}if("o"===e){for(n++;n<i;n++)if("_"!==(e=t[n])){if(!Vt(t.charCodeAt(n)))return!1;r=!0}return r&&"_"!==e}}if("_"===e)return!1;for(;n<i;n++)if("_"!==(e=t[n])){if(!Kt(t.charCodeAt(n)))return!1;r=!0}return!(!r||"_"===e)},construct:function(t){var e,i=t,n=1;if(-1!==i.indexOf("_")&&(i=i.replace(/_/g,"")),"-"!==(e=i[0])&&"+"!==e||("-"===e&&(n=-1),e=(i=i.slice(1))[0]),"0"===i)return 0;if("0"===e){if("b"===i[1])return n*parseInt(i.slice(2),2);if("x"===i[1])return n*parseInt(i.slice(2),16);if("o"===i[1])return n*parseInt(i.slice(2),8)}return n*parseInt(i,10)},predicate:function(t){return"[object Number]"===Object.prototype.toString.call(t)&&t%1==0&&!Tt.isNegativeZero(t)},represent:{binary:function(t){return t>=0?"0b"+t.toString(2):"-0b"+t.toString(2).slice(1)},octal:function(t){return t>=0?"0o"+t.toString(8):"-0o"+t.toString(8).slice(1)},decimal:function(t){return t.toString(10)},hexadecimal:function(t){return t>=0?"0x"+t.toString(16).toUpperCase():"-0x"+t.toString(16).toUpperCase().slice(1)}},defaultStyle:"decimal",styleAliases:{binary:[2,"bin"],octal:[8,"oct"],decimal:[10,"dec"],hexadecimal:[16,"hex"]}}),Jt=new RegExp("^(?:[-+]?(?:[0-9][0-9_]*)(?:\\.[0-9_]*)?(?:[eE][-+]?[0-9]+)?|\\.[0-9_]+(?:[eE][-+]?[0-9]+)?|[-+]?\\.(?:inf|Inf|INF)|\\.(?:nan|NaN|NAN))$");var Zt=/^[-+]?[0-9]+e/;var Qt=new zt("tag:yaml.org,2002:float",{kind:"scalar",resolve:function(t){return null!==t&&!(!Jt.test(t)||"_"===t[t.length-1])},construct:function(t){var e,i;return i="-"===(e=t.replace(/_/g,"").toLowerCase())[0]?-1:1,"+-".indexOf(e[0])>=0&&(e=e.slice(1)),".inf"===e?1===i?Number.POSITIVE_INFINITY:Number.NEGATIVE_INFINITY:".nan"===e?NaN:i*parseFloat(e,10)},predicate:function(t){return"[object Number]"===Object.prototype.toString.call(t)&&(t%1!=0||Tt.isNegativeZero(t))},represent:function(t,e){var i;if(isNaN(t))switch(e){case"lowercase":return".nan";case"uppercase":return".NAN";case"camelcase":return".NaN"}else if(Number.POSITIVE_INFINITY===t)switch(e){case"lowercase":return".inf";case"uppercase":return".INF";case"camelcase":return".Inf"}else if(Number.NEGATIVE_INFINITY===t)switch(e){case"lowercase":return"-.inf";case"uppercase":return"-.INF";case"camelcase":return"-.Inf"}else if(Tt.isNegativeZero(t))return"-0.0";return i=t.toString(10),Zt.test(i)?i.replace("e",".e"):i},defaultStyle:"lowercase"}),Xt=Bt.extend({implicit:[Ht,qt,Gt,Qt]}),te=new RegExp("^([0-9][0-9][0-9][0-9])-([0-9][0-9])-([0-9][0-9])$"),ee=new RegExp("^([0-9][0-9][0-9][0-9])-([0-9][0-9]?)-([0-9][0-9]?)(?:[Tt]|[ \\t]+)([0-9][0-9]?):([0-9][0-9]):([0-9][0-9])(?:\\.([0-9]*))?(?:[ \\t]*(Z|([-+])([0-9][0-9]?)(?::([0-9][0-9]))?))?$");var ie=new zt("tag:yaml.org,2002:timestamp",{kind:"scalar",resolve:function(t){return null!==t&&(null!==te.exec(t)||null!==ee.exec(t))},construct:function(t){var e,i,n,r,o,s,a,l,c=0,d=null;if(null===(e=te.exec(t))&&(e=ee.exec(t)),null===e)throw new Error("Date resolve error");if(i=+e[1],n=+e[2]-1,r=+e[3],!e[4])return new Date(Date.UTC(i,n,r));if(o=+e[4],s=+e[5],a=+e[6],e[7]){for(c=e[7].slice(0,3);c.length<3;)c+="0";c=+c}return e[9]&&(d=6e4*(60*+e[10]+ +(e[11]||0)),"-"===e[9]&&(d=-d)),l=new Date(Date.UTC(i,n,r,o,s,a,c)),d&&l.setTime(l.getTime()-d),l},instanceOf:Date,represent:function(t){return t.toISOString()}});var ne=new zt("tag:yaml.org,2002:merge",{kind:"scalar",resolve:function(t){return"<<"===t||null===t}}),re="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r";var oe=new zt("tag:yaml.org,2002:binary",{kind:"scalar",resolve:function(t){if(null===t)return!1;var e,i,n=0,r=t.length,o=re;for(i=0;i<r;i++)if(!((e=o.indexOf(t.charAt(i)))>64)){if(e<0)return!1;n+=6}return n%8==0},construct:function(t){var e,i,n=t.replace(/[\r\n=]/g,""),r=n.length,o=re,s=0,a=[];for(e=0;e<r;e++)e%4==0&&e&&(a.push(s>>16&255),a.push(s>>8&255),a.push(255&s)),s=s<<6|o.indexOf(n.charAt(e));return 0===(i=r%4*6)?(a.push(s>>16&255),a.push(s>>8&255),a.push(255&s)):18===i?(a.push(s>>10&255),a.push(s>>2&255)):12===i&&a.push(s>>4&255),new Uint8Array(a)},predicate:function(t){return"[object Uint8Array]"===Object.prototype.toString.call(t)},represent:function(t){var e,i,n="",r=0,o=t.length,s=re;for(e=0;e<o;e++)e%3==0&&e&&(n+=s[r>>18&63],n+=s[r>>12&63],n+=s[r>>6&63],n+=s[63&r]),r=(r<<8)+t[e];return 0===(i=o%3)?(n+=s[r>>18&63],n+=s[r>>12&63],n+=s[r>>6&63],n+=s[63&r]):2===i?(n+=s[r>>10&63],n+=s[r>>4&63],n+=s[r<<2&63],n+=s[64]):1===i&&(n+=s[r>>2&63],n+=s[r<<4&63],n+=s[64],n+=s[64]),n}}),se=Object.prototype.hasOwnProperty,ae=Object.prototype.toString;var le=new zt("tag:yaml.org,2002:omap",{kind:"sequence",resolve:function(t){if(null===t)return!0;var e,i,n,r,o,s=[],a=t;for(e=0,i=a.length;e<i;e+=1){if(n=a[e],o=!1,"[object Object]"!==ae.call(n))return!1;for(r in n)if(se.call(n,r)){if(o)return!1;o=!0}if(!o)return!1;if(-1!==s.indexOf(r))return!1;s.push(r)}return!0},construct:function(t){return null!==t?t:[]}}),ce=Object.prototype.toString;var de=new zt("tag:yaml.org,2002:pairs",{kind:"sequence",resolve:function(t){if(null===t)return!0;var e,i,n,r,o,s=t;for(o=new Array(s.length),e=0,i=s.length;e<i;e+=1){if(n=s[e],"[object Object]"!==ce.call(n))return!1;if(1!==(r=Object.keys(n)).length)return!1;o[e]=[r[0],n[r[0]]]}return!0},construct:function(t){if(null===t)return[];var e,i,n,r,o,s=t;for(o=new Array(s.length),e=0,i=s.length;e<i;e+=1)n=s[e],r=Object.keys(n),o[e]=[r[0],n[r[0]]];return o}}),ue=Object.prototype.hasOwnProperty;var he=new zt("tag:yaml.org,2002:set",{kind:"mapping",resolve:function(t){if(null===t)return!0;var e,i=t;for(e in i)if(ue.call(i,e)&&null!==i[e])return!1;return!0},construct:function(t){return null!==t?t:{}}}),pe=Xt.extend({implicit:[ie,ne],explicit:[oe,le,de,he]}),fe=Object.prototype.hasOwnProperty,ge=/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x84\x86-\x9F\uFFFE\uFFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]/,be=/[\x85\u2028\u2029]/,ve=/[,\[\]\{\}]/,me=/^(?:!|!!|![a-z\-]+!)$/i,_e=/^(?:!|[^,\[\]\{\}])(?:%[0-9a-f]{2}|[0-9a-z\-#;\/\?:@&=\+\$,_\.!~\*'\(\)\[\]])*$/i;function ye(t){return Object.prototype.toString.call(t)}function $e(t){return 10===t||13===t}function we(t){return 9===t||32===t}function xe(t){return 9===t||32===t||10===t||13===t}function Ae(t){return 44===t||91===t||93===t||123===t||125===t}function ke(t){var e;return 48<=t&&t<=57?t-48:97<=(e=32|t)&&e<=102?e-97+10:-1}function Ee(t){return 120===t?2:117===t?4:85===t?8:0}function Ce(t){return 48<=t&&t<=57?t-48:-1}function Se(t){return 48===t?"\0":97===t?"":98===t?"\b":116===t||9===t?"\t":110===t?"\n":118===t?"\v":102===t?"\f":114===t?"\r":101===t?"":32===t?" ":34===t?'"':47===t?"/":92===t?"\\":78===t?"":95===t?" ":76===t?"\u2028":80===t?"\u2029":""}function Oe(t){return t<=65535?String.fromCharCode(t):String.fromCharCode(55296+(t-65536>>10),56320+(t-65536&1023))}for(var Ie=new Array(256),Te=new Array(256),je=0;je<256;je++)Ie[je]=Se(je)?1:0,Te[je]=Se(je);function Ne(t,e){this.input=t,this.filename=e.filename||null,this.schema=e.schema||pe,this.onWarning=e.onWarning||null,this.legacy=e.legacy||!1,this.json=e.json||!1,this.listener=e.listener||null,this.implicitTypes=this.schema.compiledImplicit,this.typeMap=this.schema.compiledTypeMap,this.length=t.length,this.position=0,this.line=0,this.lineStart=0,this.lineIndent=0,this.firstTabInLine=-1,this.documents=[]}function Me(t,e){var i={name:t.filename,buffer:t.input.slice(0,-1),position:t.position,line:t.line,column:t.position-t.lineStart};return i.snippet=Dt(i),new Mt(e,i)}function Re(t,e){throw Me(t,e)}function Pe(t,e){t.onWarning&&t.onWarning.call(null,Me(t,e))}var De={YAML:function(t,e,i){var n,r,o;null!==t.version&&Re(t,"duplication of %YAML directive"),1!==i.length&&Re(t,"YAML directive accepts exactly one argument"),null===(n=/^([0-9]+)\.([0-9]+)$/.exec(i[0]))&&Re(t,"ill-formed argument of the YAML directive"),r=parseInt(n[1],10),o=parseInt(n[2],10),1!==r&&Re(t,"unacceptable YAML version of the document"),t.version=i[0],t.checkLineBreaks=o<2,1!==o&&2!==o&&Pe(t,"unsupported YAML version of the document")},TAG:function(t,e,i){var n,r;2!==i.length&&Re(t,"TAG directive accepts exactly two arguments"),n=i[0],r=i[1],me.test(n)||Re(t,"ill-formed tag handle (first argument) of the TAG directive"),fe.call(t.tagMap,n)&&Re(t,'there is a previously declared suffix for "'+n+'" tag handle'),_e.test(r)||Re(t,"ill-formed tag prefix (second argument) of the TAG directive");try{r=decodeURIComponent(r)}catch(e){Re(t,"tag prefix is malformed: "+r)}t.tagMap[n]=r}};function Ue(t,e,i,n){var r,o,s,a;if(e<i){if(a=t.input.slice(e,i),n)for(r=0,o=a.length;r<o;r+=1)9===(s=a.charCodeAt(r))||32<=s&&s<=1114111||Re(t,"expected valid JSON character");else ge.test(a)&&Re(t,"the stream contains non-printable characters");t.result+=a}}function We(t,e,i,n){var r,o,s,a;for(Tt.isObject(i)||Re(t,"cannot merge mappings; the provided source object is unacceptable"),s=0,a=(r=Object.keys(i)).length;s<a;s+=1)o=r[s],fe.call(e,o)||(e[o]=i[o],n[o]=!0)}function ze(t,e,i,n,r,o,s,a,l){var c,d;if(Array.isArray(r))for(c=0,d=(r=Array.prototype.slice.call(r)).length;c<d;c+=1)Array.isArray(r[c])&&Re(t,"nested arrays are not supported inside keys"),"object"==typeof r&&"[object Object]"===ye(r[c])&&(r[c]="[object Object]");if("object"==typeof r&&"[object Object]"===ye(r)&&(r="[object Object]"),r=String(r),null===e&&(e={}),"tag:yaml.org,2002:merge"===n)if(Array.isArray(o))for(c=0,d=o.length;c<d;c+=1)We(t,e,o[c],i);else We(t,e,o,i);else t.json||fe.call(i,r)||!fe.call(e,r)||(t.line=s||t.line,t.lineStart=a||t.lineStart,t.position=l||t.position,Re(t,"duplicated mapping key")),"__proto__"===r?Object.defineProperty(e,r,{configurable:!0,enumerable:!0,writable:!0,value:o}):e[r]=o,delete i[r];return e}function Le(t){var e;10===(e=t.input.charCodeAt(t.position))?t.position++:13===e?(t.position++,10===t.input.charCodeAt(t.position)&&t.position++):Re(t,"a line break is expected"),t.line+=1,t.lineStart=t.position,t.firstTabInLine=-1}function Fe(t,e,i){for(var n=0,r=t.input.charCodeAt(t.position);0!==r;){for(;we(r);)9===r&&-1===t.firstTabInLine&&(t.firstTabInLine=t.position),r=t.input.charCodeAt(++t.position);if(e&&35===r)do{r=t.input.charCodeAt(++t.position)}while(10!==r&&13!==r&&0!==r);if(!$e(r))break;for(Le(t),r=t.input.charCodeAt(t.position),n++,t.lineIndent=0;32===r;)t.lineIndent++,r=t.input.charCodeAt(++t.position)}return-1!==i&&0!==n&&t.lineIndent<i&&Pe(t,"deficient indentation"),n}function Be(t){var e,i=t.position;return!(45!==(e=t.input.charCodeAt(i))&&46!==e||e!==t.input.charCodeAt(i+1)||e!==t.input.charCodeAt(i+2)||(i+=3,0!==(e=t.input.charCodeAt(i))&&!xe(e)))}function He(t,e){1===e?t.result+=" ":e>1&&(t.result+=Tt.repeat("\n",e-1))}function qe(t,e){var i,n,r=t.tag,o=t.anchor,s=[],a=!1;if(-1!==t.firstTabInLine)return!1;for(null!==t.anchor&&(t.anchorMap[t.anchor]=s),n=t.input.charCodeAt(t.position);0!==n&&(-1!==t.firstTabInLine&&(t.position=t.firstTabInLine,Re(t,"tab characters must not be used in indentation")),45===n)&&xe(t.input.charCodeAt(t.position+1));)if(a=!0,t.position++,Fe(t,!0,-1)&&t.lineIndent<=e)s.push(null),n=t.input.charCodeAt(t.position);else if(i=t.line,Ke(t,e,3,!1,!0),s.push(t.result),Fe(t,!0,-1),n=t.input.charCodeAt(t.position),(t.line===i||t.lineIndent>e)&&0!==n)Re(t,"bad indentation of a sequence entry");else if(t.lineIndent<e)break;return!!a&&(t.tag=r,t.anchor=o,t.kind="sequence",t.result=s,!0)}function Ye(t){var e,i,n,r,o=!1,s=!1;if(33!==(r=t.input.charCodeAt(t.position)))return!1;if(null!==t.tag&&Re(t,"duplication of a tag property"),60===(r=t.input.charCodeAt(++t.position))?(o=!0,r=t.input.charCodeAt(++t.position)):33===r?(s=!0,i="!!",r=t.input.charCodeAt(++t.position)):i="!",e=t.position,o){do{r=t.input.charCodeAt(++t.position)}while(0!==r&&62!==r);t.position<t.length?(n=t.input.slice(e,t.position),r=t.input.charCodeAt(++t.position)):Re(t,"unexpected end of the stream within a verbatim tag")}else{for(;0!==r&&!xe(r);)33===r&&(s?Re(t,"tag suffix cannot contain exclamation marks"):(i=t.input.slice(e-1,t.position+1),me.test(i)||Re(t,"named tag handle cannot contain such characters"),s=!0,e=t.position+1)),r=t.input.charCodeAt(++t.position);n=t.input.slice(e,t.position),ve.test(n)&&Re(t,"tag suffix cannot contain flow indicator characters")}n&&!_e.test(n)&&Re(t,"tag name cannot contain such characters: "+n);try{n=decodeURIComponent(n)}catch(e){Re(t,"tag name is malformed: "+n)}return o?t.tag=n:fe.call(t.tagMap,i)?t.tag=t.tagMap[i]+n:"!"===i?t.tag="!"+n:"!!"===i?t.tag="tag:yaml.org,2002:"+n:Re(t,'undeclared tag handle "'+i+'"'),!0}function Ve(t){var e,i;if(38!==(i=t.input.charCodeAt(t.position)))return!1;for(null!==t.anchor&&Re(t,"duplication of an anchor property"),i=t.input.charCodeAt(++t.position),e=t.position;0!==i&&!xe(i)&&!Ae(i);)i=t.input.charCodeAt(++t.position);return t.position===e&&Re(t,"name of an anchor node must contain at least one character"),t.anchor=t.input.slice(e,t.position),!0}function Ke(t,e,i,n,r){var o,s,a,l,c,d,u,h,p,f=1,g=!1,b=!1;if(null!==t.listener&&t.listener("open",t),t.tag=null,t.anchor=null,t.kind=null,t.result=null,o=s=a=4===i||3===i,n&&Fe(t,!0,-1)&&(g=!0,t.lineIndent>e?f=1:t.lineIndent===e?f=0:t.lineIndent<e&&(f=-1)),1===f)for(;Ye(t)||Ve(t);)Fe(t,!0,-1)?(g=!0,a=o,t.lineIndent>e?f=1:t.lineIndent===e?f=0:t.lineIndent<e&&(f=-1)):a=!1;if(a&&(a=g||r),1!==f&&4!==i||(h=1===i||2===i?e:e+1,p=t.position-t.lineStart,1===f?a&&(qe(t,p)||function(t,e,i){var n,r,o,s,a,l,c,d=t.tag,u=t.anchor,h={},p=Object.create(null),f=null,g=null,b=null,v=!1,m=!1;if(-1!==t.firstTabInLine)return!1;for(null!==t.anchor&&(t.anchorMap[t.anchor]=h),c=t.input.charCodeAt(t.position);0!==c;){if(v||-1===t.firstTabInLine||(t.position=t.firstTabInLine,Re(t,"tab characters must not be used in indentation")),n=t.input.charCodeAt(t.position+1),o=t.line,63!==c&&58!==c||!xe(n)){if(s=t.line,a=t.lineStart,l=t.position,!Ke(t,i,2,!1,!0))break;if(t.line===o){for(c=t.input.charCodeAt(t.position);we(c);)c=t.input.charCodeAt(++t.position);if(58===c)xe(c=t.input.charCodeAt(++t.position))||Re(t,"a whitespace character is expected after the key-value separator within a block mapping"),v&&(ze(t,h,p,f,g,null,s,a,l),f=g=b=null),m=!0,v=!1,r=!1,f=t.tag,g=t.result;else{if(!m)return t.tag=d,t.anchor=u,!0;Re(t,"can not read an implicit mapping pair; a colon is missed")}}else{if(!m)return t.tag=d,t.anchor=u,!0;Re(t,"can not read a block mapping entry; a multiline key may not be an implicit key")}}else 63===c?(v&&(ze(t,h,p,f,g,null,s,a,l),f=g=b=null),m=!0,v=!0,r=!0):v?(v=!1,r=!0):Re(t,"incomplete explicit mapping pair; a key node is missed; or followed by a non-tabulated empty line"),t.position+=1,c=n;if((t.line===o||t.lineIndent>e)&&(v&&(s=t.line,a=t.lineStart,l=t.position),Ke(t,e,4,!0,r)&&(v?g=t.result:b=t.result),v||(ze(t,h,p,f,g,b,s,a,l),f=g=b=null),Fe(t,!0,-1),c=t.input.charCodeAt(t.position)),(t.line===o||t.lineIndent>e)&&0!==c)Re(t,"bad indentation of a mapping entry");else if(t.lineIndent<e)break}return v&&ze(t,h,p,f,g,null,s,a,l),m&&(t.tag=d,t.anchor=u,t.kind="mapping",t.result=h),m}(t,p,h))||function(t,e){var i,n,r,o,s,a,l,c,d,u,h,p,f=!0,g=t.tag,b=t.anchor,v=Object.create(null);if(91===(p=t.input.charCodeAt(t.position)))s=93,c=!1,o=[];else{if(123!==p)return!1;s=125,c=!0,o={}}for(null!==t.anchor&&(t.anchorMap[t.anchor]=o),p=t.input.charCodeAt(++t.position);0!==p;){if(Fe(t,!0,e),(p=t.input.charCodeAt(t.position))===s)return t.position++,t.tag=g,t.anchor=b,t.kind=c?"mapping":"sequence",t.result=o,!0;f?44===p&&Re(t,"expected the node content, but found ','"):Re(t,"missed comma between flow collection entries"),h=null,a=l=!1,63===p&&xe(t.input.charCodeAt(t.position+1))&&(a=l=!0,t.position++,Fe(t,!0,e)),i=t.line,n=t.lineStart,r=t.position,Ke(t,e,1,!1,!0),u=t.tag,d=t.result,Fe(t,!0,e),p=t.input.charCodeAt(t.position),!l&&t.line!==i||58!==p||(a=!0,p=t.input.charCodeAt(++t.position),Fe(t,!0,e),Ke(t,e,1,!1,!0),h=t.result),c?ze(t,o,v,u,d,h,i,n,r):a?o.push(ze(t,null,v,u,d,h,i,n,r)):o.push(d),Fe(t,!0,e),44===(p=t.input.charCodeAt(t.position))?(f=!0,p=t.input.charCodeAt(++t.position)):f=!1}Re(t,"unexpected end of the stream within a flow collection")}(t,h)?b=!0:(s&&function(t,e){var i,n,r,o,s=1,a=!1,l=!1,c=e,d=0,u=!1;if(124===(o=t.input.charCodeAt(t.position)))n=!1;else{if(62!==o)return!1;n=!0}for(t.kind="scalar",t.result="";0!==o;)if(43===(o=t.input.charCodeAt(++t.position))||45===o)1===s?s=43===o?3:2:Re(t,"repeat of a chomping mode identifier");else{if(!((r=Ce(o))>=0))break;0===r?Re(t,"bad explicit indentation width of a block scalar; it cannot be less than one"):l?Re(t,"repeat of an indentation width identifier"):(c=e+r-1,l=!0)}if(we(o)){do{o=t.input.charCodeAt(++t.position)}while(we(o));if(35===o)do{o=t.input.charCodeAt(++t.position)}while(!$e(o)&&0!==o)}for(;0!==o;){for(Le(t),t.lineIndent=0,o=t.input.charCodeAt(t.position);(!l||t.lineIndent<c)&&32===o;)t.lineIndent++,o=t.input.charCodeAt(++t.position);if(!l&&t.lineIndent>c&&(c=t.lineIndent),$e(o))d++;else{if(t.lineIndent<c){3===s?t.result+=Tt.repeat("\n",a?1+d:d):1===s&&a&&(t.result+="\n");break}for(n?we(o)?(u=!0,t.result+=Tt.repeat("\n",a?1+d:d)):u?(u=!1,t.result+=Tt.repeat("\n",d+1)):0===d?a&&(t.result+=" "):t.result+=Tt.repeat("\n",d):t.result+=Tt.repeat("\n",a?1+d:d),a=!0,l=!0,d=0,i=t.position;!$e(o)&&0!==o;)o=t.input.charCodeAt(++t.position);Ue(t,i,t.position,!1)}}return!0}(t,h)||function(t,e){var i,n,r;if(39!==(i=t.input.charCodeAt(t.position)))return!1;for(t.kind="scalar",t.result="",t.position++,n=r=t.position;0!==(i=t.input.charCodeAt(t.position));)if(39===i){if(Ue(t,n,t.position,!0),39!==(i=t.input.charCodeAt(++t.position)))return!0;n=t.position,t.position++,r=t.position}else $e(i)?(Ue(t,n,r,!0),He(t,Fe(t,!1,e)),n=r=t.position):t.position===t.lineStart&&Be(t)?Re(t,"unexpected end of the document within a single quoted scalar"):(t.position++,r=t.position);Re(t,"unexpected end of the stream within a single quoted scalar")}(t,h)||function(t,e){var i,n,r,o,s,a;if(34!==(a=t.input.charCodeAt(t.position)))return!1;for(t.kind="scalar",t.result="",t.position++,i=n=t.position;0!==(a=t.input.charCodeAt(t.position));){if(34===a)return Ue(t,i,t.position,!0),t.position++,!0;if(92===a){if(Ue(t,i,t.position,!0),$e(a=t.input.charCodeAt(++t.position)))Fe(t,!1,e);else if(a<256&&Ie[a])t.result+=Te[a],t.position++;else if((s=Ee(a))>0){for(r=s,o=0;r>0;r--)(s=ke(a=t.input.charCodeAt(++t.position)))>=0?o=(o<<4)+s:Re(t,"expected hexadecimal character");t.result+=Oe(o),t.position++}else Re(t,"unknown escape sequence");i=n=t.position}else $e(a)?(Ue(t,i,n,!0),He(t,Fe(t,!1,e)),i=n=t.position):t.position===t.lineStart&&Be(t)?Re(t,"unexpected end of the document within a double quoted scalar"):(t.position++,n=t.position)}Re(t,"unexpected end of the stream within a double quoted scalar")}(t,h)?b=!0:!function(t){var e,i,n;if(42!==(n=t.input.charCodeAt(t.position)))return!1;for(n=t.input.charCodeAt(++t.position),e=t.position;0!==n&&!xe(n)&&!Ae(n);)n=t.input.charCodeAt(++t.position);return t.position===e&&Re(t,"name of an alias node must contain at least one character"),i=t.input.slice(e,t.position),fe.call(t.anchorMap,i)||Re(t,'unidentified alias "'+i+'"'),t.result=t.anchorMap[i],Fe(t,!0,-1),!0}(t)?function(t,e,i){var n,r,o,s,a,l,c,d,u=t.kind,h=t.result;if(xe(d=t.input.charCodeAt(t.position))||Ae(d)||35===d||38===d||42===d||33===d||124===d||62===d||39===d||34===d||37===d||64===d||96===d)return!1;if((63===d||45===d)&&(xe(n=t.input.charCodeAt(t.position+1))||i&&Ae(n)))return!1;for(t.kind="scalar",t.result="",r=o=t.position,s=!1;0!==d;){if(58===d){if(xe(n=t.input.charCodeAt(t.position+1))||i&&Ae(n))break}else if(35===d){if(xe(t.input.charCodeAt(t.position-1)))break}else{if(t.position===t.lineStart&&Be(t)||i&&Ae(d))break;if($e(d)){if(a=t.line,l=t.lineStart,c=t.lineIndent,Fe(t,!1,-1),t.lineIndent>=e){s=!0,d=t.input.charCodeAt(t.position);continue}t.position=o,t.line=a,t.lineStart=l,t.lineIndent=c;break}}s&&(Ue(t,r,o,!1),He(t,t.line-a),r=o=t.position,s=!1),we(d)||(o=t.position+1),d=t.input.charCodeAt(++t.position)}return Ue(t,r,o,!1),!!t.result||(t.kind=u,t.result=h,!1)}(t,h,1===i)&&(b=!0,null===t.tag&&(t.tag="?")):(b=!0,null===t.tag&&null===t.anchor||Re(t,"alias node should not have any properties")),null!==t.anchor&&(t.anchorMap[t.anchor]=t.result)):0===f&&(b=a&&qe(t,p))),null===t.tag)null!==t.anchor&&(t.anchorMap[t.anchor]=t.result);else if("?"===t.tag){for(null!==t.result&&"scalar"!==t.kind&&Re(t,'unacceptable node kind for !<?> tag; it should be "scalar", not "'+t.kind+'"'),l=0,c=t.implicitTypes.length;l<c;l+=1)if((u=t.implicitTypes[l]).resolve(t.result)){t.result=u.construct(t.result),t.tag=u.tag,null!==t.anchor&&(t.anchorMap[t.anchor]=t.result);break}}else if("!"!==t.tag){if(fe.call(t.typeMap[t.kind||"fallback"],t.tag))u=t.typeMap[t.kind||"fallback"][t.tag];else for(u=null,l=0,c=(d=t.typeMap.multi[t.kind||"fallback"]).length;l<c;l+=1)if(t.tag.slice(0,d[l].tag.length)===d[l].tag){u=d[l];break}u||Re(t,"unknown tag !<"+t.tag+">"),null!==t.result&&u.kind!==t.kind&&Re(t,"unacceptable node kind for !<"+t.tag+'> tag; it should be "'+u.kind+'", not "'+t.kind+'"'),u.resolve(t.result,t.tag)?(t.result=u.construct(t.result,t.tag),null!==t.anchor&&(t.anchorMap[t.anchor]=t.result)):Re(t,"cannot resolve a node with !<"+t.tag+"> explicit tag")}return null!==t.listener&&t.listener("close",t),null!==t.tag||null!==t.anchor||b}function Ge(t){var e,i,n,r,o=t.position,s=!1;for(t.version=null,t.checkLineBreaks=t.legacy,t.tagMap=Object.create(null),t.anchorMap=Object.create(null);0!==(r=t.input.charCodeAt(t.position))&&(Fe(t,!0,-1),r=t.input.charCodeAt(t.position),!(t.lineIndent>0||37!==r));){for(s=!0,r=t.input.charCodeAt(++t.position),e=t.position;0!==r&&!xe(r);)r=t.input.charCodeAt(++t.position);for(n=[],(i=t.input.slice(e,t.position)).length<1&&Re(t,"directive name must not be less than one character in length");0!==r;){for(;we(r);)r=t.input.charCodeAt(++t.position);if(35===r){do{r=t.input.charCodeAt(++t.position)}while(0!==r&&!$e(r));break}if($e(r))break;for(e=t.position;0!==r&&!xe(r);)r=t.input.charCodeAt(++t.position);n.push(t.input.slice(e,t.position))}0!==r&&Le(t),fe.call(De,i)?De[i](t,i,n):Pe(t,'unknown document directive "'+i+'"')}Fe(t,!0,-1),0===t.lineIndent&&45===t.input.charCodeAt(t.position)&&45===t.input.charCodeAt(t.position+1)&&45===t.input.charCodeAt(t.position+2)?(t.position+=3,Fe(t,!0,-1)):s&&Re(t,"directives end mark is expected"),Ke(t,t.lineIndent-1,4,!1,!0),Fe(t,!0,-1),t.checkLineBreaks&&be.test(t.input.slice(o,t.position))&&Pe(t,"non-ASCII line breaks are interpreted as content"),t.documents.push(t.result),t.position===t.lineStart&&Be(t)?46===t.input.charCodeAt(t.position)&&(t.position+=3,Fe(t,!0,-1)):t.position<t.length-1&&Re(t,"end of the stream or a document separator is expected")}var Je={load:function(t,e){var i=function(t,e){e=e||{},0!==(t=String(t)).length&&(10!==t.charCodeAt(t.length-1)&&13!==t.charCodeAt(t.length-1)&&(t+="\n"),65279===t.charCodeAt(0)&&(t=t.slice(1)));var i=new Ne(t,e),n=t.indexOf("\0");for(-1!==n&&(i.position=n,Re(i,"null byte is not allowed in input")),i.input+="\0";32===i.input.charCodeAt(i.position);)i.lineIndent+=1,i.position+=1;for(;i.position<i.length-1;)Ge(i);return i.documents}(t,e);if(0!==i.length){if(1===i.length)return i[0];throw new Mt("expected a single document in the stream, but found more")}}},Ze=Object.prototype.toString,Qe=Object.prototype.hasOwnProperty,Xe=65279,ti={0:"\\0",7:"\\a",8:"\\b",9:"\\t",10:"\\n",11:"\\v",12:"\\f",13:"\\r",27:"\\e",34:'\\"',92:"\\\\",133:"\\N",160:"\\_",8232:"\\L",8233:"\\P"},ei=["y","Y","yes","Yes","YES","on","On","ON","n","N","no","No","NO","off","Off","OFF"],ii=/^[-+]?[0-9_]+(?::[0-9_]+)+(?:\.[0-9_]*)?$/;function ni(t){var e,i,n;if(e=t.toString(16).toUpperCase(),t<=255)i="x",n=2;else if(t<=65535)i="u",n=4;else{if(!(t<=4294967295))throw new Mt("code point within a string may not be greater than 0xFFFFFFFF");i="U",n=8}return"\\"+i+Tt.repeat("0",n-e.length)+e}function ri(t){this.schema=t.schema||pe,this.indent=Math.max(1,t.indent||2),this.noArrayIndent=t.noArrayIndent||!1,this.skipInvalid=t.skipInvalid||!1,this.flowLevel=Tt.isNothing(t.flowLevel)?-1:t.flowLevel,this.styleMap=function(t,e){var i,n,r,o,s,a,l;if(null===e)return{};for(i={},r=0,o=(n=Object.keys(e)).length;r<o;r+=1)s=n[r],a=String(e[s]),"!!"===s.slice(0,2)&&(s="tag:yaml.org,2002:"+s.slice(2)),(l=t.compiledTypeMap.fallback[s])&&Qe.call(l.styleAliases,a)&&(a=l.styleAliases[a]),i[s]=a;return i}(this.schema,t.styles||null),this.sortKeys=t.sortKeys||!1,this.lineWidth=t.lineWidth||80,this.noRefs=t.noRefs||!1,this.noCompatMode=t.noCompatMode||!1,this.condenseFlow=t.condenseFlow||!1,this.quotingType='"'===t.quotingType?2:1,this.forceQuotes=t.forceQuotes||!1,this.replacer="function"==typeof t.replacer?t.replacer:null,this.implicitTypes=this.schema.compiledImplicit,this.explicitTypes=this.schema.compiledExplicit,this.tag=null,this.result="",this.duplicates=[],this.usedDuplicates=null}function oi(t,e){for(var i,n=Tt.repeat(" ",e),r=0,o=-1,s="",a=t.length;r<a;)-1===(o=t.indexOf("\n",r))?(i=t.slice(r),r=a):(i=t.slice(r,o+1),r=o+1),i.length&&"\n"!==i&&(s+=n),s+=i;return s}function si(t,e){return"\n"+Tt.repeat(" ",t.indent*e)}function ai(t){return 32===t||9===t}function li(t){return 32<=t&&t<=126||161<=t&&t<=55295&&8232!==t&&8233!==t||57344<=t&&t<=65533&&t!==Xe||65536<=t&&t<=1114111}function ci(t){return li(t)&&t!==Xe&&13!==t&&10!==t}function di(t,e,i){var n=ci(t),r=n&&!ai(t);return(i?n:n&&44!==t&&91!==t&&93!==t&&123!==t&&125!==t)&&35!==t&&!(58===e&&!r)||ci(e)&&!ai(e)&&35===t||58===e&&r}function ui(t,e){var i,n=t.charCodeAt(e);return n>=55296&&n<=56319&&e+1<t.length&&(i=t.charCodeAt(e+1))>=56320&&i<=57343?1024*(n-55296)+i-56320+65536:n}function hi(t){return/^\n* /.test(t)}function pi(t,e,i,n,r,o,s,a){var l,c=0,d=null,u=!1,h=!1,p=-1!==n,f=-1,g=function(t){return li(t)&&t!==Xe&&!ai(t)&&45!==t&&63!==t&&58!==t&&44!==t&&91!==t&&93!==t&&123!==t&&125!==t&&35!==t&&38!==t&&42!==t&&33!==t&&124!==t&&61!==t&&62!==t&&39!==t&&34!==t&&37!==t&&64!==t&&96!==t}(ui(t,0))&&function(t){return!ai(t)&&58!==t}(ui(t,t.length-1));if(e||s)for(l=0;l<t.length;c>=65536?l+=2:l++){if(!li(c=ui(t,l)))return 5;g=g&&di(c,d,a),d=c}else{for(l=0;l<t.length;c>=65536?l+=2:l++){if(10===(c=ui(t,l)))u=!0,p&&(h=h||l-f-1>n&&" "!==t[f+1],f=l);else if(!li(c))return 5;g=g&&di(c,d,a),d=c}h=h||p&&l-f-1>n&&" "!==t[f+1]}return u||h?i>9&&hi(t)?5:s?2===o?5:2:h?4:3:!g||s||r(t)?2===o?5:2:1}function fi(t,e,i,n,r){t.dump=function(){if(0===e.length)return 2===t.quotingType?'""':"''";if(!t.noCompatMode&&(-1!==ei.indexOf(e)||ii.test(e)))return 2===t.quotingType?'"'+e+'"':"'"+e+"'";var o=t.indent*Math.max(1,i),s=-1===t.lineWidth?-1:Math.max(Math.min(t.lineWidth,40),t.lineWidth-o),a=n||t.flowLevel>-1&&i>=t.flowLevel;switch(pi(e,a,t.indent,s,function(e){return function(t,e){var i,n;for(i=0,n=t.implicitTypes.length;i<n;i+=1)if(t.implicitTypes[i].resolve(e))return!0;return!1}(t,e)},t.quotingType,t.forceQuotes&&!n,r)){case 1:return e;case 2:return"'"+e.replace(/'/g,"''")+"'";case 3:return"|"+gi(e,t.indent)+bi(oi(e,o));case 4:return">"+gi(e,t.indent)+bi(oi(function(t,e){var i,n,r=/(\n+)([^\n]*)/g,o=(a=t.indexOf("\n"),a=-1!==a?a:t.length,r.lastIndex=a,vi(t.slice(0,a),e)),s="\n"===t[0]||" "===t[0];var a;for(;n=r.exec(t);){var l=n[1],c=n[2];i=" "===c[0],o+=l+(s||i||""===c?"":"\n")+vi(c,e),s=i}return o}(e,s),o));case 5:return'"'+function(t){for(var e,i="",n=0,r=0;r<t.length;n>=65536?r+=2:r++)n=ui(t,r),!(e=ti[n])&&li(n)?(i+=t[r],n>=65536&&(i+=t[r+1])):i+=e||ni(n);return i}(e)+'"';default:throw new Mt("impossible error: invalid scalar style")}}()}function gi(t,e){var i=hi(t)?String(e):"",n="\n"===t[t.length-1];return i+(n&&("\n"===t[t.length-2]||"\n"===t)?"+":n?"":"-")+"\n"}function bi(t){return"\n"===t[t.length-1]?t.slice(0,-1):t}function vi(t,e){if(""===t||" "===t[0])return t;for(var i,n,r=/ [^ ]/g,o=0,s=0,a=0,l="";i=r.exec(t);)(a=i.index)-o>e&&(n=s>o?s:a,l+="\n"+t.slice(o,n),o=n+1),s=a;return l+="\n",t.length-o>e&&s>o?l+=t.slice(o,s)+"\n"+t.slice(s+1):l+=t.slice(o),l.slice(1)}function mi(t,e,i,n){var r,o,s,a="",l=t.tag;for(r=0,o=i.length;r<o;r+=1)s=i[r],t.replacer&&(s=t.replacer.call(i,String(r),s)),(yi(t,e+1,s,!0,!0,!1,!0)||void 0===s&&yi(t,e+1,null,!0,!0,!1,!0))&&(n&&""===a||(a+=si(t,e)),t.dump&&10===t.dump.charCodeAt(0)?a+="-":a+="- ",a+=t.dump);t.tag=l,t.dump=a||"[]"}function _i(t,e,i){var n,r,o,s,a,l;for(o=0,s=(r=i?t.explicitTypes:t.implicitTypes).length;o<s;o+=1)if(((a=r[o]).instanceOf||a.predicate)&&(!a.instanceOf||"object"==typeof e&&e instanceof a.instanceOf)&&(!a.predicate||a.predicate(e))){if(i?a.multi&&a.representName?t.tag=a.representName(e):t.tag=a.tag:t.tag="?",a.represent){if(l=t.styleMap[a.tag]||a.defaultStyle,"[object Function]"===Ze.call(a.represent))n=a.represent(e,l);else{if(!Qe.call(a.represent,l))throw new Mt("!<"+a.tag+'> tag resolver accepts not "'+l+'" style');n=a.represent[l](e,l)}t.dump=n}return!0}return!1}function yi(t,e,i,n,r,o,s){t.tag=null,t.dump=i,_i(t,i,!1)||_i(t,i,!0);var a,l=Ze.call(t.dump),c=n;n&&(n=t.flowLevel<0||t.flowLevel>e);var d,u,h="[object Object]"===l||"[object Array]"===l;if(h&&(u=-1!==(d=t.duplicates.indexOf(i))),(null!==t.tag&&"?"!==t.tag||u||2!==t.indent&&e>0)&&(r=!1),u&&t.usedDuplicates[d])t.dump="*ref_"+d;else{if(h&&u&&!t.usedDuplicates[d]&&(t.usedDuplicates[d]=!0),"[object Object]"===l)n&&0!==Object.keys(t.dump).length?(!function(t,e,i,n){var r,o,s,a,l,c,d="",u=t.tag,h=Object.keys(i);if(!0===t.sortKeys)h.sort();else if("function"==typeof t.sortKeys)h.sort(t.sortKeys);else if(t.sortKeys)throw new Mt("sortKeys must be a boolean or a function");for(r=0,o=h.length;r<o;r+=1)c="",n&&""===d||(c+=si(t,e)),a=i[s=h[r]],t.replacer&&(a=t.replacer.call(i,s,a)),yi(t,e+1,s,!0,!0,!0)&&((l=null!==t.tag&&"?"!==t.tag||t.dump&&t.dump.length>1024)&&(t.dump&&10===t.dump.charCodeAt(0)?c+="?":c+="? "),c+=t.dump,l&&(c+=si(t,e)),yi(t,e+1,a,!0,l)&&(t.dump&&10===t.dump.charCodeAt(0)?c+=":":c+=": ",d+=c+=t.dump));t.tag=u,t.dump=d||"{}"}(t,e,t.dump,r),u&&(t.dump="&ref_"+d+t.dump)):(!function(t,e,i){var n,r,o,s,a,l="",c=t.tag,d=Object.keys(i);for(n=0,r=d.length;n<r;n+=1)a="",""!==l&&(a+=", "),t.condenseFlow&&(a+='"'),s=i[o=d[n]],t.replacer&&(s=t.replacer.call(i,o,s)),yi(t,e,o,!1,!1)&&(t.dump.length>1024&&(a+="? "),a+=t.dump+(t.condenseFlow?'"':"")+":"+(t.condenseFlow?"":" "),yi(t,e,s,!1,!1)&&(l+=a+=t.dump));t.tag=c,t.dump="{"+l+"}"}(t,e,t.dump),u&&(t.dump="&ref_"+d+" "+t.dump));else if("[object Array]"===l)n&&0!==t.dump.length?(t.noArrayIndent&&!s&&e>0?mi(t,e-1,t.dump,r):mi(t,e,t.dump,r),u&&(t.dump="&ref_"+d+t.dump)):(!function(t,e,i){var n,r,o,s="",a=t.tag;for(n=0,r=i.length;n<r;n+=1)o=i[n],t.replacer&&(o=t.replacer.call(i,String(n),o)),(yi(t,e,o,!1,!1)||void 0===o&&yi(t,e,null,!1,!1))&&(""!==s&&(s+=","+(t.condenseFlow?"":" ")),s+=t.dump);t.tag=a,t.dump="["+s+"]"}(t,e,t.dump),u&&(t.dump="&ref_"+d+" "+t.dump));else{if("[object String]"!==l){if("[object Undefined]"===l)return!1;if(t.skipInvalid)return!1;throw new Mt("unacceptable kind of an object to dump "+l)}"?"!==t.tag&&fi(t,t.dump,e,o,c)}null!==t.tag&&"?"!==t.tag&&(a=encodeURI("!"===t.tag[0]?t.tag.slice(1):t.tag).replace(/!/g,"%21"),a="!"===t.tag[0]?"!"+a:"tag:yaml.org,2002:"===a.slice(0,18)?"!!"+a.slice(18):"!<"+a+">",t.dump=a+" "+t.dump)}return!0}function $i(t,e){var i,n,r=[],o=[];for(wi(t,r,o),i=0,n=o.length;i<n;i+=1)e.duplicates.push(r[o[i]]);e.usedDuplicates=new Array(n)}function wi(t,e,i){var n,r,o;if(null!==t&&"object"==typeof t)if(-1!==(r=e.indexOf(t)))-1===i.indexOf(r)&&i.push(r);else if(e.push(t),Array.isArray(t))for(r=0,o=t.length;r<o;r+=1)wi(t[r],e,i);else for(r=0,o=(n=Object.keys(t)).length;r<o;r+=1)wi(t[n[r]],e,i)}var xi=Je.load,Ai={dump:function(t,e){var i=new ri(e=e||{});i.noRefs||$i(t,i);var n=t;return i.replacer&&(n=i.replacer.call({"":n},"",n)),yi(i,0,n,!0,!0)?i.dump+"\n":""}}.dump;const ki={condition:"state"};let Ei=class extends at{constructor(){super(...arguments),this.value=[],this.disabled=!1,this.language="en",this._errors={},this._onAdd=()=>{this._emit([...this.value,{...ki}])}}get hasError(){return Object.keys(this._errors).length>0}render(){return B`
      <div class="wrap">
        <div class="help">${gt(this.language,"conditions_help")}</div>
        ${this.value.map((t,e)=>this._row(t,e))}
        <button
          class="add-condition"
          ?disabled=${this.disabled}
          @click=${this._onAdd}
        >
          ${gt(this.language,"add_condition")}
        </button>
      </div>
    `}_row(t,e){const i=this._errors[e];return B`
      <div class="condition-row">
        <div class="body">
          <textarea
            .value=${Ai(t).trimEnd()}
            ?disabled=${this.disabled}
            @change=${t=>this._onEdit(t,e)}
          ></textarea>
          ${i?B`<div class="row-error">${i}</div>`:q}
        </div>
        <button
          class="remove-condition"
          ?disabled=${this.disabled}
          @click=${()=>this._onRemove(e)}
        >
          ${gt(this.language,"remove_condition")}
        </button>
      </div>
    `}_emit(t){this.dispatchEvent(new CustomEvent("condition-changed",{detail:{value:t}}))}_setError(t,e){const i={...this._errors};null===e?delete i[t]:i[t]=e,this._errors=i}_onEdit(t,e){const i=t.target.value;let n;try{n=xi(i)}catch{return void this._setError(e,gt(this.language,"condition_unparseable"))}if(null===n||"object"!=typeof n||Array.isArray(n))return void this._setError(e,gt(this.language,"condition_not_a_mapping"));this._setError(e,null);const r=[...this.value];r[e]=n,this._emit(r)}_onRemove(t){const e={};for(const[i,n]of Object.entries(this._errors)){const r=Number(i);r<t?e[r]=n:r>t&&(e[r-1]=n)}this._errors=e,this._emit(this.value.filter((e,i)=>i!==t))}};Ei.styles=s`
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
  `,t([ht({attribute:!1})],Ei.prototype,"value",void 0),t([ht({type:Boolean})],Ei.prototype,"disabled",void 0),t([ht()],Ei.prototype,"language",void 0),t([pt()],Ei.prototype,"_errors",void 0),Ei=t([ct("shabbat-condition-editor")],Ei);let Ci=class extends at{constructor(){super(...arguments),this.hass=null,this.value={enabled:!1},this.disabled=!1,this.language="en",this._onEnabled=t=>{const e=Boolean(t.detail?.value);this._emit(e?{enabled:!0,within:this.value.within??"01:00:00"}:{enabled:!1})},this._onWithin=t=>{const e=t.detail?.value;var i;this._emit(void 0===e?{enabled:!0}:{enabled:!0,within:(i=e,[i?.hours??0,i?.minutes??0,i?.seconds??0].map(t=>String(t).padStart(2,"0")).join(":"))})}}render(){return B`
      <div class="wrap">
        <div class="field">
          <label for="replay-enabled">
            ${gt(this.language,"replay_after_restart")}
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
                ${gt(this.language,"replay_within_label")}
              </label>
              <ha-selector
                id="replay-within"
                class="replay-within"
                .hass=${this.hass}
                .selector=${{duration:{}}}
                .value=${function(t){if(void 0===t)return;const e=t.split(":");if(3!==e.length)return;if(!e.every(t=>/^\d+$/.test(t)))return;const[i,n,r]=e.map(t=>Number(t));return{hours:i,minutes:n,seconds:r}}(this.value.within)}
                .disabled=${this.disabled}
                @value-changed=${this._onWithin}
              ></ha-selector>
            </div>`:B`<div class="help">${gt(this.language,"replay_help")}</div>`}
      </div>
    `}_emit(t){this.dispatchEvent(new CustomEvent("replay-changed",{detail:{value:t}}))}};Ci.styles=s`
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
  `,t([ht({attribute:!1})],Ci.prototype,"hass",void 0),t([ht({attribute:!1})],Ci.prototype,"value",void 0),t([ht({type:Boolean})],Ci.prototype,"disabled",void 0),t([ht()],Ci.prototype,"language",void 0),Ci=t([ct("shabbat-replay-editor")],Ci);let Si=class extends at{constructor(){super(...arguments),this.hass=null,this.action="",this.data={},this.disabled=!1,this._onChange=t=>{const e=t.detail?.value??{},i={action:"string"==typeof e.action?e.action:""};"object"==typeof e.data&&null!==e.data&&(i.data=e.data),this.dispatchEvent(new CustomEvent("service-changed",{detail:i}))},this._observer=null}render(){return B`
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
    `}get _control(){return this.shadowRoot?.querySelector("ha-service-control")??null}async updated(){const t=this._control;t?.updateComplete&&await t.updateComplete,this.suppressTargetRows(),this._watch()}disconnectedCallback(){super.disconnectedCallback(),this._observer?.disconnect(),this._observer=null}_watch(){const t=this._control?.shadowRoot;!this._observer&&t&&(this._observer=new MutationObserver(()=>this.suppressTargetRows()),this._observer.observe(t,{childList:!0}))}suppressTargetRows(){const t=this._control?.shadowRoot;if(!t)return 0;const e=[...t.querySelectorAll("ha-selector")].filter(t=>{const e=t.selector;return"object"==typeof e&&null!==e&&"target"in e});for(const t of e)t.style.setProperty("display","none","important");return this.setAttribute("data-target-rows-suppressed",String(e.length)),e.length}};Si.styles=s`
    :host { display: block; }
  `,t([ht({attribute:!1})],Si.prototype,"hass",void 0),t([ht()],Si.prototype,"action",void 0),t([ht({attribute:!1})],Si.prototype,"data",void 0),t([ht({type:Boolean})],Si.prototype,"disabled",void 0),Si=t([ct("shabbat-service-editor")],Si);let Oi=class extends at{constructor(){super(...arguments),this.hass=null,this.value={},this.inherited={},this.disabled=!1,this.language="en",this._onChange=t=>{const e=t.detail?.value??{};this.dispatchEvent(new CustomEvent("target-changed",{detail:{value:e}}))}}render(){const t=yt(this.value),e=yt(this.inherited),i=""===t&&""!==e;return B`
      <div class="wrap">
        <ha-selector
          .hass=${this.hass}
          .selector=${{target:{}}}
          .value=${this.value}
          .disabled=${this.disabled}
          @value-changed=${this._onChange}
        ></ha-selector>
        ${i?B`<div class="note inherited">
              ${gt(this.language,"inherits_target_from_defaults")}
              ${e}
            </div>`:""===t?B`<div class="note empty">${gt(this.language,"target_none")}</div>`:q}
      </div>
    `}};Oi.styles=s`
    .note {
      color: var(--secondary-text-color, #666);
      font-size: 0.85em;
      margin-block-start: 4px;
      overflow-wrap: anywhere;
    }
  `,t([ht({attribute:!1})],Oi.prototype,"hass",void 0),t([ht({attribute:!1})],Oi.prototype,"value",void 0),t([ht({attribute:!1})],Oi.prototype,"inherited",void 0),t([ht({type:Boolean})],Oi.prototype,"disabled",void 0),t([ht()],Oi.prototype,"language",void 0),Oi=t([ct("shabbat-target-editor")],Oi);const Ii={day:"erev",time:"",action:"",target:{},data:{},condition:[],replay:{enabled:!1},name:null,icon:null,color:null,enabled:!0};let Ti=class extends at{constructor(){super(...arguments),this.hass=null,this.rule=null,this.seed=null,this.day="erev",this.profile=1,this.defaults={},this.canWrite=!1,this.busy=!1,this.error=null,this.language="en",this._form=Ii,this._advanced=!1,this._conditionError=!1,this._seeded=null}willUpdate(){const t=this.rule?`edit:${this.rule.id}`:`new:${this.day}:${this.profile}:${JSON.stringify(this.seed)}`;var e;this._seeded!==t&&(this._seeded=t,this.rule?this._form={day:(e=this.rule).day,time:e.time,action:e.action,target:{...e.target},data:{...e.data},condition:e.condition.map(t=>({...t})),replay:{...e.replay},name:e.name,icon:e.icon,color:e.color,enabled:e.enabled}:this.seed?this._form={...this.seed,day:this.day}:this._form={...Ii,day:this.day},this._advanced=!1)}_patch(t){this._form={...this._form,...t}}_emit(t){this.dispatchEvent(new CustomEvent(t,{detail:{form:this._form,rule:this.rule}}))}_text(t,e){return B`
      <div class="field">
        <label for=${t}>${e}</label>
        <input
          id=${t}
          class=${t}
          .value=${String(this._form[t]??"")}
          ?disabled=${!this.canWrite}
          @change=${e=>{const i=e.target.value;this._patch({[t]:""===i?null:i})}}
        />
      </div>
    `}_timeField(){return B`
      <div class="field">
        <label for="time">${gt(this.language,"time")}</label>
        <ha-selector
          id="time"
          class="time"
          .hass=${this.hass}
          .selector=${{time:{}}}
          .value=${this._form.time||null}
          .disabled=${!this.canWrite}
          @value-changed=${t=>this._patch({time:t.detail?.value??""})}
        ></ha-selector>
      </div>
    `}_enabledField(){return B`
      <div class="field">
        <label for="enabled">${gt(this.language,"enabled")}</label>
        <ha-selector
          id="enabled"
          class="enabled"
          .hass=${this.hass}
          .selector=${{boolean:{}}}
          .value=${this._form.enabled}
          .disabled=${!this.canWrite}
          @value-changed=${t=>this._patch({enabled:Boolean(t.detail?.value)})}
        ></ha-selector>
      </div>
    `}_iconField(){return B`
      <div class="field">
        <label for="icon">${gt(this.language,"icon")}</label>
        <ha-selector
          id="icon"
          class="icon"
          .hass=${this.hass}
          .selector=${{icon:{}}}
          .value=${this._form.icon??""}
          .disabled=${!this.canWrite}
          @value-changed=${t=>{const e=t.detail?.value??"";this._patch({icon:""===e?null:e})}}
        ></ha-selector>
      </div>
    `}_colorField(){return B`
      <div class="field">
        <label for="color">${gt(this.language,"colour")}</label>
        <input
          id="color"
          class="color"
          type="color"
          .value=${this._form.color||"#000000"}
          ?disabled=${!this.canWrite}
          @change=${t=>{this._patch({color:t.target.value})}}
        />
      </div>
    `}_onSave(){const t=this.shadowRoot?.querySelector("shabbat-condition-editor");t?.hasError?this._conditionError=!0:(this._conditionError=!1,this._emit("dialog-save"))}render(){const t=null!==this.rule;return B`
      <div class="sheet" @click=${t=>{t.target===t.currentTarget&&this.dispatchEvent(new CustomEvent("dialog-close"))}}>
        <div class="panel">
          <h2>${gt(this.language,t?"edit_rule":"add_rule")}</h2>

          ${this.canWrite?q:B`<div class="note">${gt(this.language,"read_only")}</div>`}
          ${this.rule?.migration_error?B`<div class="migration">
                ${gt(this.language,"migration_error")} ${this.rule.migration_error}
              </div>`:q}
          ${null!==this.error?B`<div class="error">${this.error}</div>`:q}
          ${this._conditionError?B`<div class="error condition-blocked">
                ${gt(this.language,"condition_unparseable")}
              </div>`:q}

          <div class="form">
            ${this._timeField()}
            ${this._text("name",gt(this.language,"name"))}

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
              @service-changed=${t=>this._patch({action:t.detail.action,data:t.detail.data??{}})}
            ></shabbat-service-editor>

            <shabbat-target-editor
              .hass=${this.hass}
              .value=${this._form.target}
              .inherited=${this.defaults.target??{}}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @target-changed=${t=>this._patch({target:t.detail.value})}
            ></shabbat-target-editor>

            <shabbat-condition-editor
              .value=${this._form.condition}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @condition-changed=${t=>{const e=t.target;this._conditionError=!0===e.hasError,this._patch({condition:t.detail.value})}}
            ></shabbat-condition-editor>

            <shabbat-replay-editor
              .hass=${this.hass}
              .value=${this._form.replay}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @replay-changed=${t=>this._patch({replay:t.detail.value})}
            ></shabbat-replay-editor>

            <button
              class="advanced-toggle"
              @click=${()=>{this._advanced=!this._advanced}}
            >
              ${gt(this.language,"advanced")}
            </button>
            ${this._advanced?B`
                  <div class="advanced">
                    ${this._iconField()}
                    ${this._colorField()}
                  </div>
                `:q}
          </div>

          <div class="actions">
            ${this.canWrite&&t?B`<button
                  class="delete"
                  ?disabled=${this.busy}
                  @click=${()=>this._emit("dialog-delete")}
                >
                  ${gt(this.language,"delete_rule")}
                </button>`:q}
            <button @click=${()=>this.dispatchEvent(new CustomEvent("dialog-close"))}>
              ${gt(this.language,"cancel")}
            </button>
            ${this.canWrite&&t?B`<button
                  class="duplicate"
                  ?disabled=${this.busy}
                  @click=${()=>this._emit("dialog-duplicate")}
                >
                  ${gt(this.language,"duplicate")}
                </button>`:q}
            ${this.canWrite?B`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${()=>this._onSave()}
                >
                  ${gt(this.language,"save")}
                </button>`:q}
          </div>
        </div>
      </div>
    `}};Ti.styles=s`
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
  `,t([ht({attribute:!1})],Ti.prototype,"hass",void 0),t([ht({attribute:!1})],Ti.prototype,"rule",void 0),t([ht({attribute:!1})],Ti.prototype,"seed",void 0),t([ht()],Ti.prototype,"day",void 0),t([ht({type:Number})],Ti.prototype,"profile",void 0),t([ht({attribute:!1})],Ti.prototype,"defaults",void 0),t([ht({type:Boolean})],Ti.prototype,"canWrite",void 0),t([ht({type:Boolean})],Ti.prototype,"busy",void 0),t([ht()],Ti.prototype,"error",void 0),t([ht()],Ti.prototype,"language",void 0),t([pt()],Ti.prototype,"_form",void 0),t([pt()],Ti.prototype,"_advanced",void 0),t([pt()],Ti.prototype,"_conditionError",void 0),Ti=t([ct("shabbat-rule-dialog")],Ti);let ji=class extends at{constructor(){super(...arguments),this.hass=null,this.defaults={},this.canWrite=!1,this.busy=!1,this.error=null,this.language="en",this._draft={},this._action="",this._seeded=!1,this._onServiceChanged=t=>{const e=t.detail;this._action="string"==typeof e.action?e.action:"","data"in e&&(this._draft={...this._draft,data:e.data})}}willUpdate(){this._seeded||(this._seeded=!0,this._draft={target:this.defaults.target??{},data:this.defaults.data??{}})}_onSave(){this.dispatchEvent(new CustomEvent("dialog-save",{detail:{defaults:{target:this._draft.target??{},data:this._draft.data??{}}}}))}render(){return B`
      <div class="sheet" @click=${t=>{t.target===t.currentTarget&&this.dispatchEvent(new CustomEvent("dialog-close"))}}>
        <div class="panel">
          <h2>${gt(this.language,"defaults_title")}</h2>
          <div class="note">${gt(this.language,"defaults_help")}</div>
          ${null!==this.error?B`<div class="error">${this.error}</div>`:q}

          <div class="form">
            <div class="section">
              <div class="label">${gt(this.language,"target")}</div>
              <shabbat-target-editor
                .hass=${this.hass}
                .value=${this._draft.target??{}}
                .disabled=${!this.canWrite}
                .language=${this.language}
                @target-changed=${t=>{this._draft={...this._draft,target:t.detail.value}}}
              ></shabbat-target-editor>
            </div>
            <div class="section">
              <div class="label">${gt(this.language,"data")}</div>
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
              ${gt(this.language,"cancel")}
            </button>
            ${this.canWrite?B`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${()=>this._onSave()}
                >
                  ${gt(this.language,"save")}
                </button>`:q}
          </div>
        </div>
      </div>
    `}};ji.styles=s`
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
  `,t([ht({attribute:!1})],ji.prototype,"hass",void 0),t([ht({attribute:!1})],ji.prototype,"defaults",void 0),t([ht({type:Boolean})],ji.prototype,"canWrite",void 0),t([ht({type:Boolean})],ji.prototype,"busy",void 0),t([ht()],ji.prototype,"error",void 0),t([ht()],ji.prototype,"language",void 0),t([pt()],ji.prototype,"_draft",void 0),t([pt()],ji.prototype,"_action",void 0),ji=t([ct("shabbat-defaults-dialog")],ji);const Ni="not_set_up";let Mi=class extends at{constructor(){super(...arguments),this._state=null,this._error=null,this._config={},this._selectedProfile=null,this._editing=null,this._creatingDay=null,this._defaultsOpen=!1,this._dialogError=null,this._toggleErrors={},this._busy=!1,this._duplicateSeed=null,this._unsubscribe=null,this._subscribed=!1,this._generation=0,this._onMaster=t=>{const{enabled:e}=t.detail,i=this._state?.master_entity_id;i&&this._call("switch",e?"turn_on":"turn_off",{entity_id:i})},this._onDryRun=t=>{const{dryRun:e}=t.detail;this._call("shabbat_scheduler","set_dry_run",{enabled:e})},this._closeDialogs=()=>{this._editing=null,this._creatingDay=null,this._duplicateSeed=null,this._defaultsOpen=!1,this._dialogError=null},this._onRuleOpen=t=>{this._editing=t.detail.rule,this._creatingDay=null,this._duplicateSeed=null,this._dialogError=null},this._onRuleToggleEnabled=t=>{const{rule:e}=t.detail;this._toggleRuleEnabled(e)},this._onRuleAdd=t=>{this._creatingDay=t.detail.day,this._editing=null,this._duplicateSeed=null,this._dialogError=null},this._onSave=async t=>{const{form:e,rule:i}=t.detail;(null===i?await this._send({type:"shabbat_scheduler/rules/create",rule:At(e,this._profile)}):await this._saveChanges(e,i))&&this._closeDialogs()},this._onDelete=async t=>{const{rule:e}=t.detail;await this._send({type:"shabbat_scheduler/rules/delete",rule_id:e.id})&&this._closeDialogs()},this._onDuplicate=t=>{const{form:e}=t.detail;this._editing=null,this._creatingDay=e.day,this._duplicateSeed=e,this._dialogError=null},this._onDefaultsSave=async t=>{const{defaults:e}=t.detail;await this._send({type:"shabbat_scheduler/defaults/update",defaults:e})&&this._closeDialogs()}}setConfig(t){this._config=t??{}}getCardSize(){return 3+this._groups.reduce((t,e)=>t+e.rules.length,0)}static getStubConfig(){return{type:"custom:shabbat-scheduler-card"}}set hass(t){const e=this._language,i=this._canWrite;this._hass=t,this._language===e&&this._canWrite===i||this.requestUpdate(),this._ensureSubscribed()}get hass(){return this._hass}_ensureSubscribed(){!this._subscribed&&this._hass&&this.isConnected&&(this._subscribed=!0,this._subscribe())}async _subscribe(){const t=this._generation;try{const e=await this._hass.connection.subscribeMessage(e=>{t===this._generation&&(this._state?.block?.length!==e.block?.length&&(this._selectedProfile=null),this._state=e,this._error=null)},{type:"shabbat_scheduler/subscribe"});if(t!==this._generation||!this.isConnected)return void this._teardown(e);this._unsubscribe=e}catch(e){if(t!==this._generation)return;this._error=function(t){const e=t?.code;if("string"==typeof e)return e===Ni;const i=t?.message;return"string"==typeof i&&i.includes(Ni)}(e)?"not_set_up":"stale",this._subscribed=!1}}async _teardown(t){if(null!==t)try{await t()}catch{}}connectedCallback(){super.connectedCallback(),this._ensureSubscribed()}disconnectedCallback(){super.disconnectedCallback(),this._generation+=1;const t=this._unsubscribe;this._unsubscribe=null,this._subscribed=!1,this._teardown(t)}get _language(){return this._hass?.locale?.language??"en"}get _canWrite(){return!0===this._hass?.user?.is_admin}get _profile(){return this._selectedProfile??this._state?.block?.length??1}get _groups(){const t=this._state;return null!==t&&Array.isArray(t.rules)?function(t,e){const{block:i}=t,n=e??i?.length??null;if(null===n)return[];const r=_t(t,n),o=String(n);return vt(n).map(e=>{const s=t.rules.filter(t=>t.profile===n&&t.day===e).sort((t,e)=>t.time.localeCompare(e.time));let a=null;r||null===i||("erev"===e?a={kind:"candle_lighting",at:i.candle_lighting}:e===o&&(a={kind:"havdalah",at:i.havdalah}));const l=r||null===i?null:i.dates[e]??null;return{day:e,date:l,rules:s,marker:a}}).sort((t,e)=>bt(t.day)-bt(e.day))}(t,this._profile):[]}async _call(t,e,i){try{await this._hass.callService(t,e,i)}catch{this._error="command_failed"}}async _send(t){this._busy=!0,this._dialogError=null;try{return await this._hass.callWS(t),!0}catch(t){const e=t;return this._dialogError=e?.message??String(t),!1}finally{this._busy=!1}}async _toggleRuleEnabled(t){try{if(await this._hass.callWS({type:"shabbat_scheduler/rules/update",rule_id:t.id,changes:{enabled:!t.enabled}}),t.id in this._toggleErrors){const e={...this._toggleErrors};delete e[t.id],this._toggleErrors=e}}catch(e){const i=e;this._toggleErrors={...this._toggleErrors,[t.id]:i?.message??String(e)}}}async _saveChanges(t,e){return this._send({type:"shabbat_scheduler/rules/update",rule_id:e.id,changes:kt(t,e)})}render(){const t=this._error;if("not_set_up"===t)return B`
        <ha-card>
          <div class="message">${gt(this._language,"not_set_up")}</div>
        </ha-card>
      `;if(null===this._state)return B`
        <ha-card>
          <div class="message">
            ${null===t?"…":gt(this._language,t)}
          </div>
        </ha-card>
      `;const e=this._groups,i=e.flatMap(t=>t.rules.map(t=>t.id));return B`
      <ha-card @rule-open=${this._onRuleOpen} @rule-toggle-enabled=${this._onRuleToggleEnabled}>
        ${this._config.title?B`<div class="title">${this._config.title}</div>`:q}
        ${null!==t?B`<div class="message notice">${gt(this._language,t)}</div>`:q}
        <shabbat-block-header
          .hass=${this._hass}
          .block=${this._state.block}
          .enabled=${this._state.enabled}
          .dryRun=${this._state.dry_run}
          .canWrite=${this._canWrite}
          .masterEntityId=${this._state.master_entity_id}
          .selectedProfile=${this._profile}
          .language=${this._language}
          @shabbat-master-toggle=${this._onMaster}
          @shabbat-dry-run-toggle=${this._onDryRun}
          @profile-selected=${t=>{this._selectedProfile=t.detail.profile}}
          @defaults-open=${()=>{this._defaultsOpen=!0}}
        ></shabbat-block-header>
        ${_t(this._state,this._profile)?B`<div class="preview">${gt(this._language,"preview_banner")}</div>`:q}
        <shabbat-warnings
          .warnings=${this._state.warnings}
          .displayedRuleIds=${i}
          .language=${this._language}
        ></shabbat-warnings>
        ${e.map(t=>B`
            <shabbat-day-group
              .hass=${this._hass}
              .group=${t}
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
              @dialog-save=${this._onSave}
              @dialog-delete=${this._onDelete}
              @dialog-duplicate=${this._onDuplicate}
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
      </ha-card>
    `}};Mi.styles=s`
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
  `,t([pt()],Mi.prototype,"_state",void 0),t([pt()],Mi.prototype,"_error",void 0),t([ht({attribute:!1})],Mi.prototype,"_config",void 0),t([pt()],Mi.prototype,"_selectedProfile",void 0),t([pt()],Mi.prototype,"_editing",void 0),t([pt()],Mi.prototype,"_creatingDay",void 0),t([pt()],Mi.prototype,"_defaultsOpen",void 0),t([pt()],Mi.prototype,"_dialogError",void 0),t([pt()],Mi.prototype,"_toggleErrors",void 0),t([pt()],Mi.prototype,"_busy",void 0),t([pt()],Mi.prototype,"_duplicateSeed",void 0),Mi=t([ct("shabbat-scheduler-card")],Mi),window.customCards=window.customCards??[],window.customCards.push({type:"shabbat-scheduler-card",name:"Shabbat Scheduler",description:"The coming Shabbat or Chag as a timeline."}),console.info("shabbat-scheduler-card 0.5.0");export{Mi as ShabbatSchedulerCard};
