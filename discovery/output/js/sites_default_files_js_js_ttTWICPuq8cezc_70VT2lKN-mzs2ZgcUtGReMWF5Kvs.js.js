(function ($) {

/**
 * A progressbar object. Initialized with the given id. Must be inserted into
 * the DOM afterwards through progressBar.element.
 *
 * method is the function which will perform the HTTP request to get the
 * progress bar state. Either "GET" or "POST".
 *
 * e.g. pb = new progressBar('myProgressBar');
 *      some_element.appendChild(pb.element);
 */
Drupal.progressBar = function (id, updateCallback, method, errorCallback) {
  var pb = this;
  this.id = id;
  this.method = method || 'GET';
  this.updateCallback = updateCallback;
  this.errorCallback = errorCallback;

  // The WAI-ARIA setting aria-live="polite" will announce changes after users
  // have completed their current activity and not interrupt the screen reader.
  this.element = $('<div class="progress-wrapper" aria-live="polite"></div>');
  this.element.html('<div id ="' + id + '" class="progress progress-striped active">' +
                    '<div class="progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">' +
                    '<div class="percentage sr-only"></div>' +
                    '</div></div>' +
                    '</div><div class="percentage pull-right"></div>' +
                    '<div class="message">&nbsp;</div>');
};

/**
 * Set the percentage and status message for the progressbar.
 */
Drupal.progressBar.prototype.setProgress = function (percentage, message) {
  if (percentage >= 0 && percentage <= 100) {
    $('div.progress-bar', this.element).css('width', percentage + '%');
    $('div.progress-bar', this.element).attr('aria-valuenow', percentage);
    $('div.percentage', this.element).html(percentage + '%');
  }
  $('div.message', this.element).html(message);
  if (this.updateCallback) {
    this.updateCallback(percentage, message, this);
  }
};

/**
 * Start monitoring progress via Ajax.
 */
Drupal.progressBar.prototype.startMonitoring = function (uri, delay) {
  this.delay = delay;
  this.uri = uri;
  this.sendPing();
};

/**
 * Stop monitoring progress via Ajax.
 */
Drupal.progressBar.prototype.stopMonitoring = function () {
  clearTimeout(this.timer);
  // This allows monitoring to be stopped from within the callback.
  this.uri = null;
};

/**
 * Request progress data from server.
 */
Drupal.progressBar.prototype.sendPing = function () {
  if (this.timer) {
    clearTimeout(this.timer);
  }
  if (this.uri) {
    var pb = this;
    // When doing a post request, you need non-null data. Otherwise a
    // HTTP 411 or HTTP 406 (with Apache mod_security) error may result.
    $.ajax({
      type: this.method,
      url: this.uri,
      data: '',
      dataType: 'json',
      success: function (progress) {
        // Display errors.
        if (progress.status == 0) {
          pb.displayError(progress.data);
          return;
        }
        // Update display.
        pb.setProgress(progress.percentage, progress.message);
        // Schedule next timer.
        pb.timer = setTimeout(function () { pb.sendPing(); }, pb.delay);
      },
      error: function (xmlhttp) {
        pb.displayError(Drupal.ajaxError(xmlhttp, pb.uri));
      }
    });
  }
};

/**
 * Display errors on the page.
 */
Drupal.progressBar.prototype.displayError = function (string) {
  var error = $('<div class="alert alert-block alert-error"><a class="close" data-dismiss="alert" href="#">&times;</a><h4>Error message</h4></div>').append(string);
  $(this.element).before(error).hide();

  if (this.errorCallback) {
    this.errorCallback(this);
  }
};

})(jQuery);
;
Drupal.locale = { 'pluralFormula': function ($n) { return Number(($n!=1)); }, 'strings': {"":{"An AJAX HTTP error occurred.":"Si \u00e8 verificato un errore HTTP in AJAX.","HTTP Result Code: !status":"Codice HTTP di risposta: !status","An AJAX HTTP request terminated abnormally.":"Una richiesta AJAX HTTP \u00e8 terminata in modo anomalo.","Debugging information follows.":"Di seguito le informazioni di debug.","Path: !uri":"Percorso: !uri","StatusText: !statusText":"StatusText: !statusText","ResponseText: !responseText":"ResponseText: !responseText","ReadyState: !readyState":"ReadyState: !readyState","Next":"Seguente","Cancel":"Annulla","Disabled":"Disattivato","Enabled":"Attivato","Edit":"Modifica","Search":"Cerca","Sunday":"Domenica","Monday":"Luned\u00ec","Tuesday":"Marted\u00ec","Wednesday":"Mercoled\u00ec","Thursday":"Gioved\u00ec","Friday":"Venerd\u00ec","Saturday":"Sabato","Add":"Aggiungi","Upload":"Carica","Configure":"Configura","All":"Tutti","Done":"Fatto","This field is required.":"Questo campo \u00e8 obbligatorio.","Details":"Dettagli","Prev":"Precedente","Mon":"Lun","Tue":"Mar","Wed":"Mer","Thu":"Gio","Fri":"Ven","Sat":"Sab","Sun":"Dom","January":"Gennaio","February":"Febbraio","March":"Marzo","April":"Aprile","May":"Mag","June":"Giugno","July":"Luglio","August":"Agosto","September":"Settembre","October":"Ottobre","November":"Novembre","December":"Dicembre","Show":"Mostra","Select all rows in this table":"Seleziona tutte le righe in questa tabella","Deselect all rows in this table":"Deseleziona tutte le righe in questa tabella","Today":"Oggi","Jan":"Gen","Feb":"Feb","Mar":"Mar","Apr":"Apr","Jun":"Giu","Jul":"Lug","Aug":"Ago","Sep":"Set","Oct":"Ott","Nov":"Nov","Dec":"Dic","Su":"Do","Mo":"Lu","Tu":"Ma","We":"Noi","Th":"Gi","Fr":"Ve","Sa":"Sa","Not published":"Non pubblicato","Shortcuts":"Scorciatoie","Please wait...":"Attendere prego...","Hide":"Nascondi","Loading":"Caricamento","Reports":"Resoconti","mm\/dd\/yy":"mm\/gg\/aa","Only files with the following extensions are allowed: %files-allowed.":"Sono consentiti solo i file con le seguenti estensioni: %files-allowed.","By @name on @date":"Da @name il @date","By @name":"Da @name","Not in menu":"Non nel menu","Alias: @alias":"Alias: @alias","No alias":"Nessun alias","New revision":"Nuova revisione","Drag to re-order":"Trascina per riordinare","Changes made in this table will not be saved until the form is submitted.":"I cambiamenti fatti a questa tabella non saranno salvati finch\u00e8 il form non viene inviato.","The changes to these blocks will not be saved until the \u003Cem\u003ESave blocks\u003C\/em\u003E button is clicked.":"I cambiamenti a questi blocchi non saranno salvati finch\u00e9 il bottone \u003Cem\u003ESalva blocchi\u003C\/em\u003E \u00e8 cliccato.","Show shortcuts":"Mostra scorciatoie","This permission is inherited from the authenticated user role.":"Questo permesso viene ereditato dal ruolo utente autenticato.","No revision":"Nessuna revisione","@number comments per page":"@number commenti per pagina","Requires a title":"Richiede un titolo","Not restricted":"Non limitato","(active tab)":"(scheda attiva)","Not customizable":"Non personalizzabile","Restricted to certain pages":"Limitato a certe pagine","The block cannot be placed in this region.":"Il blocco non pu\u00f2 essere posizionato in questa regione.","Hide summary":"Nascondi sommario","Edit summary":"Modifica sommario","Don\u0027t display post information":"Non mostrare le informazioni di pubblicazione","@title dialog":"Finestra di dialogo @title","The selected file %filename cannot be uploaded. Only files with the following extensions are allowed: %extensions.":"Il file selezionato %filename non pu\u00f2 essere caricato. Sono consentiti solo file con le seguenti estensioni: %extensions.","Re-order rows by numerical weight instead of dragging.":"Riordina le righe utilizzando il peso numerico invece del trascinamento.","Show row weights":"Visualizza i pesi delle righe","Hide row weights":"Nascondi i pesi delle righe","Autocomplete popup":"Popup di autocompletamento","Searching for matches...":"Ricerca in corso...","Hide shortcuts":"Nascondi scorciatoie","Other":"Altro","Hide description":"Nascondi la descrizione","Show description":"Mostra la descrizione","Content can only be inserted into CKEditor in the WYSIWYG mode.":"Il contenuto pu\u00f2 essere inserito in CKEditor solo in modalit\u00e0 WYSIWYG.","Available tokens":"Token disponibili","Insert this token into your form":"Inserisci questo token nel form","First click a text field to insert your tokens into.":"Prima occorre cliccare sul campo di testo dove inserire i token.","Loading token browser...":"Caricamento del browser dei token...","Automatic alias":"Alias automatico","Activity":"Attivit\u00e0","New":"Nuovo","No title":"Nessun titolo","Select all":"Seleziona tutto","Select":"Scegliere","No name":"Nessun nome","Remove group":"Rimuovi gruppo","Apply (all displays)":"Applica (tutte le visualizzazioni)","Apply (this display)":"Applica (solo questa visualizzazione)","Revert to default":"Ritorna al predefinito","No style":"Nessuno stile","Weight: !weight":"Peso: !weight","Pause":"Pausa","Close":"Chiudi","Unlock":"Sblocca","Log messages":"Messaggi di log","Please select a file.":"Selezionare un file.","You are not allowed to operate on more than %num files.":"L\u0027utente non \u00e8 autorizzato ad operare su pi\u00f9 di %num file.","Please specify dimensions within the allowed range that is from 1x1 to @dimensions.":"Le dimensioni specificate devono rientrare nell\u0027intervallo consentito, che va da 1x1 a @dimensions.","%filename is not an image.":"%filename non \u00e8 un\u0027immagine.","Do you want to refresh the current directory?":"Si desidera aggiornare la cartella corrente?","Delete selected files?":"Eliminare i file selezionati?","Please select a thumbnail.":"Selezionare una miniatura.","You must select at least %num files.":"Devi selezionare almeno %num file.","You can not perform this operation.":"Impossibile eseguire l\u0027operazione richiesta.","Insert file":"Inserisci file","Change view":"Cambia vista","Lock":"Blocca","Subscribe":"Iscriviti","Please wait ...":"Attendere prego ...","Are you sure you want to delete this folder and all it\\\u0027s files":"Sei sicuro di voler cancellare questa directory e tutti i suoi file","Delete this file and associated versions?":"Cancella questo file e tutte le versioni associate?","Are you sure you want to delete these selected files?":"Sei sicuro di voler eliminare i file selezionati?","Delete this file submission?":"Cancella questo file?","Unsubscribe":"Annulla iscrizione","Show File Details":"Mostra Dettagli File","Expand Folders":"Espandi Directory","File listing generated in: ":"Listing file generato in:","Loading ...":"Caricamento ...","Loading Data ...":"Caricamento Dati ...","Updating Permissions ...":"Aggiorno Permessi ...","Updating File Lock ...":"Aggiorno Blocco File ...","Notifications Disabled":"Notifiche Disabilitate","No users with Notifications Enabled":"Nessun utente con le Notifiche Abilitate","You need to enter your search terms":"E\u0027 necessario inserire i tuoi termini di ricerca","Top Level Folders":"Directory Top Level","Directory":"Cartella","You are not alllowed to create more than %num directories.":"Non puoi creare pi\u00f9 di %num cartelle.","%dirname is not a valid directory name. It should contain only alphanumeric characters, hyphen and underscore.":"%dirname non \u00e8 un nome valido. Deve contenere solo caratteri alfanumerici, trattino e underscore.","Subdirectory %dir already exists.":"La sottocartella %dir esiste gi\u00e0.","Subdirectory %dir does not exist.":"La sottocartella %dir non esiste.","Are you sure want to delete this subdirectory with all directories and files in it?":"Sei sicuro di voler eliminare questa sottocartella con tutte le cartelle ed i file al suo interno?","Using defaults":"Utilizza le impostazioni predefinite.","Scheduled for publishing":"Pianificato per la pubblicazione","Scheduled for unpublishing":"Pianificato per la rimozione della pubblicazione","Not scheduled":"Nessuna pianificazione"}} };;
(function(Drupal, $) {
  "use strict";

  $.authcache_cookie = function(name, value, lifetime) {
    lifetime = (typeof lifetime === 'undefined') ? Drupal.settings.authcache.cl : lifetime;
    $.cookie(name, value, $.extend(Drupal.settings.authcache.cp, {expires: lifetime}));
  };
}(Drupal, jQuery));
;
/*!
	Colorbox 1.6.1
	license: MIT
	http://www.jacklmoore.com/colorbox
*/
(function(t,e,i){function n(i,n,o){var r=e.createElement(i);return n&&(r.id=Z+n),o&&(r.style.cssText=o),t(r)}function o(){return i.innerHeight?i.innerHeight:t(i).height()}function r(e,i){i!==Object(i)&&(i={}),this.cache={},this.el=e,this.value=function(e){var n;return void 0===this.cache[e]&&(n=t(this.el).attr("data-cbox-"+e),void 0!==n?this.cache[e]=n:void 0!==i[e]?this.cache[e]=i[e]:void 0!==X[e]&&(this.cache[e]=X[e])),this.cache[e]},this.get=function(e){var i=this.value(e);return t.isFunction(i)?i.call(this.el,this):i}}function h(t){var e=W.length,i=(A+t)%e;return 0>i?e+i:i}function a(t,e){return Math.round((/%/.test(t)?("x"===e?E.width():o())/100:1)*parseInt(t,10))}function s(t,e){return t.get("photo")||t.get("photoRegex").test(e)}function l(t,e){return t.get("retinaUrl")&&i.devicePixelRatio>1?e.replace(t.get("photoRegex"),t.get("retinaSuffix")):e}function d(t){"contains"in y[0]&&!y[0].contains(t.target)&&t.target!==v[0]&&(t.stopPropagation(),y.focus())}function c(t){c.str!==t&&(y.add(v).removeClass(c.str).addClass(t),c.str=t)}function g(e){A=0,e&&e!==!1&&"nofollow"!==e?(W=t("."+te).filter(function(){var i=t.data(this,Y),n=new r(this,i);return n.get("rel")===e}),A=W.index(_.el),-1===A&&(W=W.add(_.el),A=W.length-1)):W=t(_.el)}function u(i){t(e).trigger(i),ae.triggerHandler(i)}function f(i){var o;if(!G){if(o=t(i).data(Y),_=new r(i,o),g(_.get("rel")),!$){$=q=!0,c(_.get("className")),y.css({visibility:"hidden",display:"block",opacity:""}),I=n(se,"LoadedContent","width:0; height:0; overflow:hidden; visibility:hidden"),b.css({width:"",height:""}).append(I),j=T.height()+k.height()+b.outerHeight(!0)-b.height(),D=C.width()+H.width()+b.outerWidth(!0)-b.width(),N=I.outerHeight(!0),z=I.outerWidth(!0);var h=a(_.get("initialWidth"),"x"),s=a(_.get("initialHeight"),"y"),l=_.get("maxWidth"),f=_.get("maxHeight");_.w=(l!==!1?Math.min(h,a(l,"x")):h)-z-D,_.h=(f!==!1?Math.min(s,a(f,"y")):s)-N-j,I.css({width:"",height:_.h}),J.position(),u(ee),_.get("onOpen"),O.add(S).hide(),y.focus(),_.get("trapFocus")&&e.addEventListener&&(e.addEventListener("focus",d,!0),ae.one(re,function(){e.removeEventListener("focus",d,!0)})),_.get("returnFocus")&&ae.one(re,function(){t(_.el).focus()})}var p=parseFloat(_.get("opacity"));v.css({opacity:p===p?p:"",cursor:_.get("overlayClose")?"pointer":"",visibility:"visible"}).show(),_.get("closeButton")?B.html(_.get("close")).appendTo(b):B.appendTo("<div/>"),w()}}function p(){y||(V=!1,E=t(i),y=n(se).attr({id:Y,"class":t.support.opacity===!1?Z+"IE":"",role:"dialog",tabindex:"-1"}).hide(),v=n(se,"Overlay").hide(),M=t([n(se,"LoadingOverlay")[0],n(se,"LoadingGraphic")[0]]),x=n(se,"Wrapper"),b=n(se,"Content").append(S=n(se,"Title"),F=n(se,"Current"),P=t('<button type="button"/>').attr({id:Z+"Previous"}),K=t('<button type="button"/>').attr({id:Z+"Next"}),R=n("button","Slideshow"),M),B=t('<button type="button"/>').attr({id:Z+"Close"}),x.append(n(se).append(n(se,"TopLeft"),T=n(se,"TopCenter"),n(se,"TopRight")),n(se,!1,"clear:left").append(C=n(se,"MiddleLeft"),b,H=n(se,"MiddleRight")),n(se,!1,"clear:left").append(n(se,"BottomLeft"),k=n(se,"BottomCenter"),n(se,"BottomRight"))).find("div div").css({"float":"left"}),L=n(se,!1,"position:absolute; width:9999px; visibility:hidden; display:none; max-width:none;"),O=K.add(P).add(F).add(R)),e.body&&!y.parent().length&&t(e.body).append(v,y.append(x,L))}function m(){function i(t){t.which>1||t.shiftKey||t.altKey||t.metaKey||t.ctrlKey||(t.preventDefault(),f(this))}return y?(V||(V=!0,K.click(function(){J.next()}),P.click(function(){J.prev()}),B.click(function(){J.close()}),v.click(function(){_.get("overlayClose")&&J.close()}),t(e).bind("keydown."+Z,function(t){var e=t.keyCode;$&&_.get("escKey")&&27===e&&(t.preventDefault(),J.close()),$&&_.get("arrowKey")&&W[1]&&!t.altKey&&(37===e?(t.preventDefault(),P.click()):39===e&&(t.preventDefault(),K.click()))}),t.isFunction(t.fn.on)?t(e).on("click."+Z,"."+te,i):t("."+te).live("click."+Z,i)),!0):!1}function w(){var e,o,r,h=J.prep,d=++le;if(q=!0,U=!1,u(he),u(ie),_.get("onLoad"),_.h=_.get("height")?a(_.get("height"),"y")-N-j:_.get("innerHeight")&&a(_.get("innerHeight"),"y"),_.w=_.get("width")?a(_.get("width"),"x")-z-D:_.get("innerWidth")&&a(_.get("innerWidth"),"x"),_.mw=_.w,_.mh=_.h,_.get("maxWidth")&&(_.mw=a(_.get("maxWidth"),"x")-z-D,_.mw=_.w&&_.w<_.mw?_.w:_.mw),_.get("maxHeight")&&(_.mh=a(_.get("maxHeight"),"y")-N-j,_.mh=_.h&&_.h<_.mh?_.h:_.mh),e=_.get("href"),Q=setTimeout(function(){M.show()},100),_.get("inline")){var c=t(e);r=t("<div>").hide().insertBefore(c),ae.one(he,function(){r.replaceWith(c)}),h(c)}else _.get("iframe")?h(" "):_.get("html")?h(_.get("html")):s(_,e)?(e=l(_,e),U=_.get("createImg"),t(U).addClass(Z+"Photo").bind("error."+Z,function(){h(n(se,"Error").html(_.get("imgError")))}).one("load",function(){d===le&&setTimeout(function(){var e;_.get("retinaImage")&&i.devicePixelRatio>1&&(U.height=U.height/i.devicePixelRatio,U.width=U.width/i.devicePixelRatio),_.get("scalePhotos")&&(o=function(){U.height-=U.height*e,U.width-=U.width*e},_.mw&&U.width>_.mw&&(e=(U.width-_.mw)/U.width,o()),_.mh&&U.height>_.mh&&(e=(U.height-_.mh)/U.height,o())),_.h&&(U.style.marginTop=Math.max(_.mh-U.height,0)/2+"px"),W[1]&&(_.get("loop")||W[A+1])&&(U.style.cursor="pointer",t(U).bind("click."+Z,function(){J.next()})),U.style.width=U.width+"px",U.style.height=U.height+"px",h(U)},1)}),U.src=e):e&&L.load(e,_.get("data"),function(e,i){d===le&&h("error"===i?n(se,"Error").html(_.get("xhrError")):t(this).contents())})}var v,y,x,b,T,C,H,k,W,E,I,L,M,S,F,R,K,P,B,O,_,j,D,N,z,A,U,$,q,G,Q,J,V,X={html:!1,photo:!1,iframe:!1,inline:!1,transition:"elastic",speed:300,fadeOut:300,width:!1,initialWidth:"600",innerWidth:!1,maxWidth:!1,height:!1,initialHeight:"450",innerHeight:!1,maxHeight:!1,scalePhotos:!0,scrolling:!0,opacity:.9,preloading:!0,className:!1,overlayClose:!0,escKey:!0,arrowKey:!0,top:!1,bottom:!1,left:!1,right:!1,fixed:!1,data:void 0,closeButton:!0,fastIframe:!0,open:!1,reposition:!0,loop:!0,slideshow:!1,slideshowAuto:!0,slideshowSpeed:2500,slideshowStart:"start slideshow",slideshowStop:"stop slideshow",photoRegex:/\.(gif|png|jp(e|g|eg)|bmp|ico|webp|jxr|svg)((#|\?).*)?$/i,retinaImage:!1,retinaUrl:!1,retinaSuffix:"@2x.$1",current:"image {current} of {total}",previous:"previous",next:"next",close:"close",xhrError:"This content failed to load.",imgError:"This image failed to load.",returnFocus:!0,trapFocus:!0,onOpen:!1,onLoad:!1,onComplete:!1,onCleanup:!1,onClosed:!1,rel:function(){return this.rel},href:function(){return t(this).attr("href")},title:function(){return this.title},createImg:function(){var e=new Image,i=t(this).data("cbox-img-attrs");return"object"==typeof i&&t.each(i,function(t,i){e[t]=i}),e},createIframe:function(){var i=e.createElement("iframe"),n=t(this).data("cbox-iframe-attrs");return"object"==typeof n&&t.each(n,function(t,e){i[t]=e}),"frameBorder"in i&&(i.frameBorder=0),"allowTransparency"in i&&(i.allowTransparency="true"),i.name=(new Date).getTime(),i.allowFullScreen=!0,i}},Y="colorbox",Z="cbox",te=Z+"Element",ee=Z+"_open",ie=Z+"_load",ne=Z+"_complete",oe=Z+"_cleanup",re=Z+"_closed",he=Z+"_purge",ae=t("<a/>"),se="div",le=0,de={},ce=function(){function t(){clearTimeout(h)}function e(){(_.get("loop")||W[A+1])&&(t(),h=setTimeout(J.next,_.get("slideshowSpeed")))}function i(){R.html(_.get("slideshowStop")).unbind(s).one(s,n),ae.bind(ne,e).bind(ie,t),y.removeClass(a+"off").addClass(a+"on")}function n(){t(),ae.unbind(ne,e).unbind(ie,t),R.html(_.get("slideshowStart")).unbind(s).one(s,function(){J.next(),i()}),y.removeClass(a+"on").addClass(a+"off")}function o(){r=!1,R.hide(),t(),ae.unbind(ne,e).unbind(ie,t),y.removeClass(a+"off "+a+"on")}var r,h,a=Z+"Slideshow_",s="click."+Z;return function(){r?_.get("slideshow")||(ae.unbind(oe,o),o()):_.get("slideshow")&&W[1]&&(r=!0,ae.one(oe,o),_.get("slideshowAuto")?i():n(),R.show())}}();t[Y]||(t(p),J=t.fn[Y]=t[Y]=function(e,i){var n,o=this;return e=e||{},t.isFunction(o)&&(o=t("<a/>"),e.open=!0),o[0]?(p(),m()&&(i&&(e.onComplete=i),o.each(function(){var i=t.data(this,Y)||{};t.data(this,Y,t.extend(i,e))}).addClass(te),n=new r(o[0],e),n.get("open")&&f(o[0])),o):o},J.position=function(e,i){function n(){T[0].style.width=k[0].style.width=b[0].style.width=parseInt(y[0].style.width,10)-D+"px",b[0].style.height=C[0].style.height=H[0].style.height=parseInt(y[0].style.height,10)-j+"px"}var r,h,s,l=0,d=0,c=y.offset();if(E.unbind("resize."+Z),y.css({top:-9e4,left:-9e4}),h=E.scrollTop(),s=E.scrollLeft(),_.get("fixed")?(c.top-=h,c.left-=s,y.css({position:"fixed"})):(l=h,d=s,y.css({position:"absolute"})),d+=_.get("right")!==!1?Math.max(E.width()-_.w-z-D-a(_.get("right"),"x"),0):_.get("left")!==!1?a(_.get("left"),"x"):Math.round(Math.max(E.width()-_.w-z-D,0)/2),l+=_.get("bottom")!==!1?Math.max(o()-_.h-N-j-a(_.get("bottom"),"y"),0):_.get("top")!==!1?a(_.get("top"),"y"):Math.round(Math.max(o()-_.h-N-j,0)/2),y.css({top:c.top,left:c.left,visibility:"visible"}),x[0].style.width=x[0].style.height="9999px",r={width:_.w+z+D,height:_.h+N+j,top:l,left:d},e){var g=0;t.each(r,function(t){return r[t]!==de[t]?(g=e,void 0):void 0}),e=g}de=r,e||y.css(r),y.dequeue().animate(r,{duration:e||0,complete:function(){n(),q=!1,x[0].style.width=_.w+z+D+"px",x[0].style.height=_.h+N+j+"px",_.get("reposition")&&setTimeout(function(){E.bind("resize."+Z,J.position)},1),t.isFunction(i)&&i()},step:n})},J.resize=function(t){var e;$&&(t=t||{},t.width&&(_.w=a(t.width,"x")-z-D),t.innerWidth&&(_.w=a(t.innerWidth,"x")),I.css({width:_.w}),t.height&&(_.h=a(t.height,"y")-N-j),t.innerHeight&&(_.h=a(t.innerHeight,"y")),t.innerHeight||t.height||(e=I.scrollTop(),I.css({height:"auto"}),_.h=I.height()),I.css({height:_.h}),e&&I.scrollTop(e),J.position("none"===_.get("transition")?0:_.get("speed")))},J.prep=function(i){function o(){return _.w=_.w||I.width(),_.w=_.mw&&_.mw<_.w?_.mw:_.w,_.w}function a(){return _.h=_.h||I.height(),_.h=_.mh&&_.mh<_.h?_.mh:_.h,_.h}if($){var d,g="none"===_.get("transition")?0:_.get("speed");I.remove(),I=n(se,"LoadedContent").append(i),I.hide().appendTo(L.show()).css({width:o(),overflow:_.get("scrolling")?"auto":"hidden"}).css({height:a()}).prependTo(b),L.hide(),t(U).css({"float":"none"}),c(_.get("className")),d=function(){function i(){t.support.opacity===!1&&y[0].style.removeAttribute("filter")}var n,o,a=W.length;$&&(o=function(){clearTimeout(Q),M.hide(),u(ne),_.get("onComplete")},S.html(_.get("title")).show(),I.show(),a>1?("string"==typeof _.get("current")&&F.html(_.get("current").replace("{current}",A+1).replace("{total}",a)).show(),K[_.get("loop")||a-1>A?"show":"hide"]().html(_.get("next")),P[_.get("loop")||A?"show":"hide"]().html(_.get("previous")),ce(),_.get("preloading")&&t.each([h(-1),h(1)],function(){var i,n=W[this],o=new r(n,t.data(n,Y)),h=o.get("href");h&&s(o,h)&&(h=l(o,h),i=e.createElement("img"),i.src=h)})):O.hide(),_.get("iframe")?(n=_.get("createIframe"),_.get("scrolling")||(n.scrolling="no"),t(n).attr({src:_.get("href"),"class":Z+"Iframe"}).one("load",o).appendTo(I),ae.one(he,function(){n.src="//about:blank"}),_.get("fastIframe")&&t(n).trigger("load")):o(),"fade"===_.get("transition")?y.fadeTo(g,1,i):i())},"fade"===_.get("transition")?y.fadeTo(g,0,function(){J.position(0,d)}):J.position(g,d)}},J.next=function(){!q&&W[1]&&(_.get("loop")||W[A+1])&&(A=h(1),f(W[A]))},J.prev=function(){!q&&W[1]&&(_.get("loop")||A)&&(A=h(-1),f(W[A]))},J.close=function(){$&&!G&&(G=!0,$=!1,u(oe),_.get("onCleanup"),E.unbind("."+Z),v.fadeTo(_.get("fadeOut")||0,0),y.stop().fadeTo(_.get("fadeOut")||0,0,function(){y.hide(),v.hide(),u(he),I.remove(),setTimeout(function(){G=!1,u(re),_.get("onClosed")},1)}))},J.remove=function(){y&&(y.stop(),t[Y].close(),y.stop(!1,!0).remove(),v.remove(),G=!1,y=null,t("."+te).removeData(Y).removeClass(te),t(e).unbind("click."+Z).unbind("keydown."+Z))},J.element=function(){return t(_.el)},J.settings=X)})(jQuery,document,window);;
(function ($) {

Drupal.behaviors.initColorbox = {
  attach: function (context, settings) {
    if (!$.isFunction($.colorbox) || typeof settings.colorbox === 'undefined') {
      return;
    }

    if (settings.colorbox.mobiledetect && window.matchMedia) {
      // Disable Colorbox for small screens.
      var mq = window.matchMedia("(max-device-width: " + settings.colorbox.mobiledevicewidth + ")");
      if (mq.matches) {
        return;
      }
    }

    $('.colorbox', context)
      .once('init-colorbox')
      .colorbox(settings.colorbox);

    $(context).bind('cbox_complete', function () {
      Drupal.attachBehaviors('#cboxLoadedContent');
    });
  }
};

})(jQuery);
;
(function ($) {

Drupal.behaviors.initColorboxDefaultStyle = {
  attach: function (context, settings) {
    $(context).bind('cbox_complete', function () {
      // Only run if there is a title.
      if ($('#cboxTitle:empty', context).length == false) {
        $('#cboxLoadedContent img', context).bind('mouseover', function () {
          $('#cboxTitle', context).slideDown();
        });
        $('#cboxOverlay', context).bind('mouseover', function () {
          $('#cboxTitle', context).slideUp();
        });
      }
      else {
        $('#cboxTitle', context).hide();
      }
    });
  }
};

})(jQuery);
;
(function ($) {

Drupal.behaviors.initColorboxLoad = {
  attach: function (context, settings) {
    if (!$.isFunction($.colorbox) || typeof settings.colorbox === 'undefined') {
      return;
    }
    $.urlParams = function (url) {
      var p = {},
          e,
          a = /\+/g,  // Regex for replacing addition symbol with a space
          r = /([^&=]+)=?([^&]*)/g,
          d = function (s) { return decodeURIComponent(s.replace(a, ' ')); },
          q = url.split('?');
      while (e = r.exec(q[1])) {
        e[1] = d(e[1]);
        e[2] = d(e[2]);
        switch (e[2].toLowerCase()) {
          case 'true':
          case 'yes':
            e[2] = true;
            break;
          case 'false':
          case 'no':
            e[2] = false;
            break;
        }
        if (e[1] == 'width') { e[1] = 'innerWidth'; }
        if (e[1] == 'height') { e[1] = 'innerHeight'; }
        p[e[1]] = e[2];
      }
      return p;
    };
    $('.colorbox-load', context)
      .once('init-colorbox-load', function () {
        var params = $.urlParams($(this).attr('href'));
        $(this).colorbox($.extend({}, settings.colorbox, params));
      });
  }
};

})(jQuery);
;
/**
 * Timeago is a jQuery plugin that makes it easy to support automatically
 * updating fuzzy timestamps (e.g. "4 minutes ago" or "about 1 day ago").
 *
 * @name timeago
 * @version 1.4.1
 * @requires jQuery v1.2.3+
 * @author Ryan McGeary
 * @license MIT License - http://www.opensource.org/licenses/mit-license.php
 *
 * For usage and examples, visit:
 * http://timeago.yarp.com/
 *
 * Copyright (c) 2008-2015, Ryan McGeary (ryan -[at]- mcgeary [*dot*] org)
 */

(function (factory) {
  if (typeof define === 'function' && define.amd) {
    // AMD. Register as an anonymous module.
    define(['jquery'], factory);
  } else {
    // Browser globals
    factory(jQuery);
  }
}(function ($) {
  $.timeago = function(timestamp) {
    if (timestamp instanceof Date) {
      return inWords(timestamp);
    } else if (typeof timestamp === "string") {
      return inWords($.timeago.parse(timestamp));
    } else if (typeof timestamp === "number") {
      return inWords(new Date(timestamp));
    } else {
      return inWords($.timeago.datetime(timestamp));
    }
  };
  var $t = $.timeago;

  $.extend($.timeago, {
    settings: {
      refreshMillis: 60000,
      allowPast: true,
      allowFuture: false,
      localeTitle: false,
      cutoff: 0,
      strings: {
        prefixAgo: null,
        prefixFromNow: null,
        suffixAgo: "ago",
        suffixFromNow: "from now",
        inPast: 'any moment now',
        seconds: "less than a minute",
        minute: "about a minute",
        minutes: "%d minutes",
        hour: "about an hour",
        hours: "about %d hours",
        day: "a day",
        days: "%d days",
        month: "about a month",
        months: "%d months",
        year: "about a year",
        years: "%d years",
        wordSeparator: " ",
        numbers: []
      }
    },

    inWords: function(distanceMillis) {
      if(!this.settings.allowPast && ! this.settings.allowFuture) {
          throw 'timeago allowPast and allowFuture settings can not both be set to false.';
      }

      var $l = this.settings.strings;
      var prefix = $l.prefixAgo;
      var suffix = $l.suffixAgo;
      if (this.settings.allowFuture) {
        if (distanceMillis < 0) {
          prefix = $l.prefixFromNow;
          suffix = $l.suffixFromNow;
        }
      }

      if(!this.settings.allowPast && distanceMillis >= 0) {
        return this.settings.strings.inPast;
      }

      var seconds = Math.abs(distanceMillis) / 1000;
      var minutes = seconds / 60;
      var hours = minutes / 60;
      var days = hours / 24;
      var years = days / 365;

      function substitute(stringOrFunction, number) {
        var string = $.isFunction(stringOrFunction) ? stringOrFunction(number, distanceMillis) : stringOrFunction;
        var value = ($l.numbers && $l.numbers[number]) || number;
        return string.replace(/%d/i, value);
      }

      var words = seconds < 45 && substitute($l.seconds, Math.round(seconds)) ||
        seconds < 90 && substitute($l.minute, 1) ||
        minutes < 45 && substitute($l.minutes, Math.round(minutes)) ||
        minutes < 90 && substitute($l.hour, 1) ||
        hours < 24 && substitute($l.hours, Math.round(hours)) ||
        hours < 42 && substitute($l.day, 1) ||
        days < 30 && substitute($l.days, Math.round(days)) ||
        days < 45 && substitute($l.month, 1) ||
        days < 365 && substitute($l.months, Math.round(days / 30)) ||
        years < 1.5 && substitute($l.year, 1) ||
        substitute($l.years, Math.round(years));

      var separator = $l.wordSeparator || "";
      if ($l.wordSeparator === undefined) { separator = " "; }
      return $.trim([prefix, words, suffix].join(separator));
    },

    parse: function(iso8601) {
      var s = $.trim(iso8601);
      s = s.replace(/\.\d+/,""); // remove milliseconds
      s = s.replace(/-/,"/").replace(/-/,"/");
      s = s.replace(/T/," ").replace(/Z/," UTC");
      s = s.replace(/([\+\-]\d\d)\:?(\d\d)/," $1$2"); // -04:00 -> -0400
      s = s.replace(/([\+\-]\d\d)$/," $100"); // +09 -> +0900
      return new Date(s);
    },
    datetime: function(elem) {
      var iso8601 = $t.isTime(elem) ? $(elem).attr("datetime") : $(elem).attr("title");
      return $t.parse(iso8601);
    },
    isTime: function(elem) {
      // jQuery's `is()` doesn't play well with HTML5 in IE
      return $(elem).get(0).tagName.toLowerCase() === "time"; // $(elem).is("time");
    }
  });

  // functions that can be called via $(el).timeago('action')
  // init is default when no action is given
  // functions are called with context of a single element
  var functions = {
    init: function(){
      var refresh_el = $.proxy(refresh, this);
      refresh_el();
      var $s = $t.settings;
      if ($s.refreshMillis > 0) {
        this._timeagoInterval = setInterval(refresh_el, $s.refreshMillis);
      }
    },
    update: function(time){
      var parsedTime = $t.parse(time);
      $(this).data('timeago', { datetime: parsedTime });
      if($t.settings.localeTitle) $(this).attr("title", parsedTime.toLocaleString());
      refresh.apply(this);
    },
    updateFromDOM: function(){
      $(this).data('timeago', { datetime: $t.parse( $t.isTime(this) ? $(this).attr("datetime") : $(this).attr("title") ) });
      refresh.apply(this);
    },
    dispose: function () {
      if (this._timeagoInterval) {
        window.clearInterval(this._timeagoInterval);
        this._timeagoInterval = null;
      }
    }
  };

  $.fn.timeago = function(action, options) {
    var fn = action ? functions[action] : functions.init;
    if(!fn){
      throw new Error("Unknown function name '"+ action +"' for timeago");
    }
    // each over objects here and call the requested function
    this.each(function(){
      fn.call(this, options);
    });
    return this;
  };

  function refresh() {
    //check if it's still visible
    if(!$.contains(document.documentElement,this)){
      //stop if it has been removed
      $(this).timeago("dispose");
      return this;
    }

    var data = prepareData(this);
    var $s = $t.settings;

    if (!isNaN(data.datetime)) {
      if ( $s.cutoff == 0 || Math.abs(distance(data.datetime)) < $s.cutoff) {
        $(this).text(inWords(data.datetime));
      }
    }
    return this;
  }

  function prepareData(element) {
    element = $(element);
    if (!element.data("timeago")) {
      element.data("timeago", { datetime: $t.datetime(element) });
      var text = $.trim(element.text());
      if ($t.settings.localeTitle) {
        element.attr("title", element.data('timeago').datetime.toLocaleString());
      } else if (text.length > 0 && !($t.isTime(element) && element.attr("title"))) {
        element.attr("title", text);
      }
    }
    return element.data("timeago");
  }

  function inWords(date) {
    return $t.inWords(distance(date));
  }

  function distance(date) {
    return (new Date().getTime() - date.getTime());
  }

  // fix for IE6 suckage
  document.createElement("abbr");
  document.createElement("time");
}));
;
(function ($) {
  Drupal.behaviors.timeago = {
    attach: function (context) {
      return;
      $.extend($.timeago.settings, Drupal.settings.timeago);
      $('abbr.timeago, span.timeago, time.timeago', context).timeago();
    }
  };
})(jQuery);
;
(function (Drupal, $) {
  "use strict";

  // Private variables
  var ajaxCount = 0;
  var timeStart = new Date().getTime();
  var cacheRenderTime = null;
  var status = {
    'Cache Status': 'Debug info pending',
  };
  var info = {};

  //
  // Private helper functions
  //
  function isNumeric(n) {
    return !isNaN(parseFloat(n)) && isFinite(n);
  }

  /**
   * Inject authcache debug widget into the page
   */
  function widget() {
    $("body").prepend("<div id='authcachedbg' style='max-width: 80em;'><div id='authcache_status_indicator'></div><strong><a href='#' id='authcachehide'>Authcache Debug</a></strong><div id='authcachedebug' style='display:none;'><div id='authcachedebuginfo'></div></div></div>");
    $("#authcachehide").click(function() {
      $("#authcachedebug").toggle();
      return false;
    });

    // Determine the render time if cache_render cookie is set.
    if ($.cookie("cache_render") && $.cookie("cache_render") !== "get") {
      cacheRenderTime = $.cookie("cache_render");
    }

    updateInfoFieldset();

    debugTimer();
  }

  /**
   * Update the info fieldset.
   */
  function updateInfoFieldset() {
    var alertColor = null;

    if (info.cacheStatus) {
      status['Cache Status'] = info.cacheStatus;

      if (info.cacheStatus === 'HIT') {
        alertColor = 'green';
      }
      else if (info.cacheStatus === 'MISS') {
        alertColor = 'orange';
      }
      else {
        alertColor = 'red';
      }
    }

    if (info.messages) {
      $.each(info.messages, function(idx, msg) {
        status['Message ' + (idx + 1)] = msg.label + ': ' + msg.message;
      });
    }

    // Determine page render time
    if (info.pageRender) {
      status["Page Render Time"] = info.pageRender + " ms";
    }

    if (info.cacheStatus === 'HIT' && cacheRenderTime !== null) {
      status["Cache Render Time"] = cacheRenderTime;

      if (isNumeric(cacheRenderTime)) {
        status["Cache Render Time"] += " ms";

        if (cacheRenderTime > 30) {
          alertColor = 'orange';
        }
        else if (cacheRenderTime > 100) {
          alertColor = 'red';
        }
      }
    }

    if (isNumeric(cacheRenderTime)) {
      status.Speedup = Math.round((info.pageRender - cacheRenderTime) / cacheRenderTime * 100).toString().replace(/(\d+)(\d{3})/, '$1' + ',' + '$2') + "% increase";
    }

    // Add some more settings and status information
    if (info.cacheTime) {
      status["Page Age"] = Math.round(timeStart / 1000 - info.cacheTime) + " seconds";
    }

    if (alertColor !== null) {
      $("#authcache_status_indicator").css({"background": alertColor});
    }

    $("#authcachedebuginfo").first().html(debugFieldset("Status", status));
    $("#authcachedebuginfo").first().append(debugFieldset("Settings", info));
  }

  /**
   * Display total JavaScript execution time for this file (including Ajax)
   */
  function debugTimer() {
    var timeMs = new Date().getTime() - timeStart;
    $("#authcachedebug").append("HTML/JavaScript time: " + timeMs + " ms <hr size=1>");
  }

  /**
   * Helper function (renders HTML fieldset)
   */
  function debugFieldset(title, jsonData) {
    var fieldset = '<div style="clear:both;"></div><fieldset style="float:left;min-width:240px;"><legend>' + title + '</legend>';
    $.each(jsonData, function(key, value) {
      if (key[0] !== key[0].toLowerCase()){
        fieldset += "<strong>" + key + "</strong>: " + JSON.stringify(value) + '<br>';
      }
    });
    fieldset += '</fieldset><div style="clear:both;">';
    return fieldset;
  }

  function isEnabled(settings) {
    return (settings.authcacheDebug && ($.cookie('aucdbg') !== null || settings.authcacheDebug.all) && typeof JSON === 'object');
  }

  // Add debug info to widget
  Drupal.behaviors.authcacheDebug = {
    attach: function (context, settings) {
      $('body').once('authcache-debug', function() {
        if (!isEnabled(settings)) {
          return;
        }

        widget();

        $.get(settings.authcacheDebug.url, function(data) {
          info = $.extend(info, data);

          updateInfoFieldset();

          $.authcache_cookie("aucdbg", Math.floor(Math.random()*65535).toString(16));
        });
      });
    }
  };

  $(window).load(function() {
    if (isEnabled(Drupal.settings)) {
      // Reset debug cookies only after all subrequests (images, JS, CSS) are completed.
      $.authcache_cookie("cache_render", "get");
    }
  });
}(Drupal, jQuery));
;

(function($) {

/**
 * Drupal FieldGroup object.
 */
Drupal.FieldGroup = Drupal.FieldGroup || {};
Drupal.FieldGroup.Effects = Drupal.FieldGroup.Effects || {};
Drupal.FieldGroup.groupWithfocus = null;

Drupal.FieldGroup.setGroupWithfocus = function(element) {
  element.css({display: 'block'});
  Drupal.FieldGroup.groupWithfocus = element;
}

/**
 * Implements Drupal.FieldGroup.processHook().
 */
Drupal.FieldGroup.Effects.processFieldset = {
  execute: function (context, settings, type) {
    if (type == 'form') {
      // Add required fields mark to any fieldsets containing required fields
      $('fieldset.fieldset', context).once('fieldgroup-effects', function(i) {
        if ($(this).is('.required-fields') && $(this).find('.form-required').length > 0) {
          $('legend span.fieldset-legend', $(this)).eq(0).append(' ').append($('.form-required').eq(0).clone());
        }
        if ($('.error', $(this)).length) {
          $('legend span.fieldset-legend', $(this)).eq(0).addClass('error');
          Drupal.FieldGroup.setGroupWithfocus($(this));
        }
      });
    }
  }
}

/**
 * Implements Drupal.FieldGroup.processHook().
 */
Drupal.FieldGroup.Effects.processAccordion = {
  execute: function (context, settings, type) {
    $('div.field-group-accordion-wrapper', context).once('fieldgroup-effects', function () {
      var wrapper = $(this);

      wrapper.accordion({
        autoHeight: false,
        active: '.field-group-accordion-active',
        collapsible: true,
        changestart: function(event, ui) {
          if ($(this).hasClass('effect-none')) {
            ui.options.animated = false;
          }
          else {
            ui.options.animated = 'slide';
          }
        }
      });

      if (type == 'form') {

        var $firstErrorItem = false;

        // Add required fields mark to any element containing required fields
        wrapper.find('div.field-group-accordion-item').each(function(i) {

          if ($(this).is('.required-fields') && $(this).find('.form-required').length > 0) {
            $('h3.ui-accordion-header a').eq(i).append(' ').append($('.form-required').eq(0).clone());
          }
          if ($('.error', $(this)).length) {
            // Save first error item, for focussing it.
            if (!$firstErrorItem) {
              $firstErrorItem = $(this).parent().accordion("activate" , i);
            }
            $('h3.ui-accordion-header').eq(i).addClass('error');
          }
        });

        // Save first error item, for focussing it.
        if (!$firstErrorItem) {
          $('.ui-accordion-content-active', $firstErrorItem).css({height: 'auto', width: 'auto', display: 'block'});
        }

      }
    });
  }
}

/**
 * Implements Drupal.FieldGroup.processHook().
 */
Drupal.FieldGroup.Effects.processHtabs = {
  execute: function (context, settings, type) {
    if (type == 'form') {
      // Add required fields mark to any element containing required fields
      $('fieldset.horizontal-tabs-pane', context).once('fieldgroup-effects', function(i) {
        if ($(this).is('.required-fields') && $(this).find('.form-required').length > 0) {
          $(this).data('horizontalTab').link.find('strong:first').after($('.form-required').eq(0).clone()).after(' ');
        }
        if ($('.error', $(this)).length) {
          $(this).data('horizontalTab').link.parent().addClass('error');
          Drupal.FieldGroup.setGroupWithfocus($(this));
          $(this).data('horizontalTab').focus();
        }
      });
    }
  }
}

/**
 * Implements Drupal.FieldGroup.processHook().
 */
Drupal.FieldGroup.Effects.processTabs = {
  execute: function (context, settings, type) {
    if (type == 'form') {
      // Add required fields mark to any fieldsets containing required fields
      $('fieldset.vertical-tabs-pane', context).once('fieldgroup-effects', function(i) {
        if ($(this).is('.required-fields') && $(this).find('.form-required').length > 0) {
          $(this).data('verticalTab').link.find('strong:first').after($('.form-required').eq(0).clone()).after(' ');
        }
        if ($('.error', $(this)).length) {
          $(this).data('verticalTab').link.parent().addClass('error');
          Drupal.FieldGroup.setGroupWithfocus($(this));
          $(this).data('verticalTab').focus();
        }
      });
    }
  }
}

/**
 * Implements Drupal.FieldGroup.processHook().
 *
 * TODO clean this up meaning check if this is really
 *      necessary.
 */
Drupal.FieldGroup.Effects.processDiv = {
  execute: function (context, settings, type) {

    $('div.collapsible', context).once('fieldgroup-effects', function() {
      var $wrapper = $(this);

      // Turn the legend into a clickable link, but retain span.field-group-format-toggler
      // for CSS positioning.

      var $toggler = $('span.field-group-format-toggler:first', $wrapper);
      var $link = $('<a class="field-group-format-title" href="#"></a>');
      $link.prepend($toggler.contents());

      // Add required field markers if needed
      if ($(this).is('.required-fields') && $(this).find('.form-required').length > 0) {
        $link.append(' ').append($('.form-required').eq(0).clone());
      }

      $link.appendTo($toggler);

      // .wrapInner() does not retain bound events.
      $link.click(function () {
        var wrapper = $wrapper.get(0);
        // Don't animate multiple times.
        if (!wrapper.animating) {
          wrapper.animating = true;
          var speed = $wrapper.hasClass('speed-fast') ? 300 : 1000;
          if ($wrapper.hasClass('effect-none') && $wrapper.hasClass('speed-none')) {
            $('> .field-group-format-wrapper', wrapper).toggle();
          }
          else if ($wrapper.hasClass('effect-blind')) {
            $('> .field-group-format-wrapper', wrapper).toggle('blind', {}, speed);
          }
          else {
            $('> .field-group-format-wrapper', wrapper).toggle(speed);
          }
          wrapper.animating = false;
        }
        $wrapper.toggleClass('collapsed');
        return false;
      });

    });
  }
};

/**
 * Behaviors.
 */
Drupal.behaviors.fieldGroup = {
  attach: function (context, settings) {
    settings.field_group = settings.field_group || Drupal.settings.field_group;
    if (settings.field_group == undefined) {
      return;
    }

    // Execute all of them.
    $.each(Drupal.FieldGroup.Effects, function (func) {
      // We check for a wrapper function in Drupal.field_group as
      // alternative for dynamic string function calls.
      var type = func.toLowerCase().replace("process", "");
      if (settings.field_group[type] != undefined && $.isFunction(this.execute)) {
        this.execute(context, settings, settings.field_group[type]);
      }
    });

    // Fixes css for fieldgroups under vertical tabs.
    $('.fieldset-wrapper .fieldset > legend').css({display: 'block'});
    $('.vertical-tabs fieldset.fieldset').addClass('default-fallback');


    // Add a new ID to each fieldset.
    $('.group-wrapper fieldset').each(function() {
      // Tats bad, but we have to keep the actual id to prevent layouts to break.
      var fieldgorupID = 'field_group-' + $(this).attr('id') + ' ' + $(this).attr('id');
      $(this).attr('id', fieldgorupID);
    })
    // Set the hash in url to remember last userselection.
    $('.group-wrapper ul li').each(function() {
      var fieldGroupNavigationListIndex = $(this).index();
      $(this).children('a').click(function() {
        var fieldset = $('.group-wrapper fieldset').get(fieldGroupNavigationListIndex);
        // Grab the first id, holding the wanted hashurl.
        var hashUrl = $(fieldset).attr('id').replace(/^field_group-/, '').split(' ')[0];
        window.location.hash = hashUrl;
      });
    });
  }
};

})(jQuery);;
(function ($) {
Drupal.settings.views = Drupal.settings.views || {'ajax_path': '/views/ajax'};

Drupal.quicktabs = Drupal.quicktabs || {};

Drupal.quicktabs.getQTName = function (el) {
  return el.id.substring(el.id.indexOf('-') +1);
}

Drupal.behaviors.quicktabs = {
  attach: function (context, settings) {
    $.extend(true, Drupal.settings, settings);
    $('.quicktabs-wrapper', context).once(function(){
      Drupal.quicktabs.prepare(this);
    });
  }
}

// Setting up the inital behaviours
Drupal.quicktabs.prepare = function(el) {
  // el.id format: "quicktabs-$name"
  var qt_name = Drupal.quicktabs.getQTName(el);
  var $ul = $(el).find('ul.quicktabs-tabs:first');
  $ul.find('li a').each(function(i, element){
    // Get tab index from link query, instead of order of this link inside
    // this group of quicktab links. This is useful when empty quicktabs are
    // hidden.
    var href = $(element).attr('href');
    var qtKey = 'qt-' + qt_name;
    var myTabIndex = getParameterByName(qtKey, href);
    element.myTabIndex = myTabIndex;
    element.qt_name = qt_name;
    var tab = new Drupal.quicktabs.tab(element);
    var parent_li = $(element).parents('li').get(0);
    if ($(parent_li).hasClass('active')) {
      $(element).addClass('quicktabs-loaded');
    }
    $(element).once(function() {$(this).bind('click', {tab: tab}, Drupal.quicktabs.clickHandler);});
  });
}

function getParameterByName(name, url) {
  name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
  var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
    results = regex.exec(url);
  return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

Drupal.quicktabs.clickHandler = function(event) {
  var tab = event.data.tab;
  var element = this;
  // Set clicked tab to active.
  $(this).parents('li').siblings().removeClass('active');
  $(this).parents('li').addClass('active');

  // Hide all tabpages.
  tab.container.children().addClass('quicktabs-hide');
  
  if (!tab.tabpage.hasClass("quicktabs-tabpage")) {
    tab = new Drupal.quicktabs.tab(element);
  }

  tab.tabpage.removeClass('quicktabs-hide');
  return false;
}

// Constructor for an individual tab
Drupal.quicktabs.tab = function (el) {
  this.element = el;
  this.tabIndex = el.myTabIndex;
  var qtKey = 'qt_' + el.qt_name;
  this.tabKey = this.tabIndex;
  this.tabObj = Drupal.settings.quicktabs[qtKey].tabs[this.tabIndex];

  this.tabpage_id = 'quicktabs-tabpage-' + el.qt_name + '-' + this.tabKey;
  this.container = $('#quicktabs-container-' + el.qt_name);
  this.tabpage = this.container.find('#' + this.tabpage_id);
}

if (Drupal.ajax) {
  /**
   * Handle an event that triggers an AJAX response.
   *
   * We unfortunately need to override this function, which originally comes from
   * misc/ajax.js, in order to be able to cache loaded tabs, i.e. once a tab
   * content has loaded it should not need to be loaded again.
   *
   * I have removed all comments that were in the original core function, so that
   * the only comments inside this function relate to the Quicktabs modification
   * of it.
   */
  Drupal.ajax.prototype.eventResponse = function (element, event) {
    var ajax = this;

    if (ajax.ajaxing) {
      return false;
    }
  
    try {
      if (ajax.form) {
        if (ajax.setClick) {
          element.form.clk = element;
        }
  
        ajax.form.ajaxSubmit(ajax.options);
      }
      else {
        // Do not perform an ajax request for already loaded Quicktabs content.
        if (!$(element).hasClass('quicktabs-loaded')) {
          ajax.beforeSerialize(ajax.element, ajax.options);
          $.ajax(ajax.options);
          if ($(element).parents('ul').hasClass('quicktabs-tabs')) {
            $(element).addClass('quicktabs-loaded');
          }
        }
      }
    }
    catch (e) {
      ajax.ajaxing = false;
      alert("An error occurred while attempting to process " + ajax.options.url + ": " + e.message);
    }
    return false;
  };
}


})(jQuery);
;
var LNP = LNP || {};

(function($) {
  Drupal.behaviors.classificaSquadra = {
    attach: function(context, settings) {
      var $classificaSquadraBlock = $('#block-lnp-classifica-squadra');

      if ($classificaSquadraBlock.length === 0) {
        return;
      }

      $classificaSquadraBlock.once('classificaSquadra', function() {
        var league = Drupal.settings.lnp_classifica_squadra.league_id;
        var year = Drupal.settings.lnp_classifica_squadra.year;
        var a2_clock_enabled = Drupal.settings.lnp_classifica_squadra.a2_clock_enabled;
        var url = '//lnpstat.domino.it/getstatisticsfiles?task=standings&round=ista&year=' + year + '&league=' + league;

        if (league.indexOf('ita2_') === 0 && a2_clock_enabled) {
          url += '&additional_league=ita2_clock&additional_round=ista';
        }

        $.get(url, function(data) {
          var selectedTeamId = Drupal.settings.lnp_classifica_squadra.team_id;

          $.each(data, function(i, team) {
            if (team.teamid == selectedTeamId) {
              var $html = $('<div class="classifica-squadra-data">' +
                '<div class="col-classifica position"><div class="value">#' + team.position + '</div><div class="label">Classifica</div></div>' +
                '<div class="col-classifica points"><div class="value">' + team.points + '</div><div class="label">Punti</div></div>' +
                '<div class="col-classifica win"><div class="value">' + team.win + '</div><div class="label">Vinte</div></div>' +
                '<div class="col-classifica loss"><div class="value">' + team.loss + '</div><div class="label">Perse</div></div>' +
                '</div>');

              $classificaSquadraBlock.find('.classifica-squadra-data-wrapper').html($html);
            }
          });
        });
      });
    }
  };

  $(document).ready(function() {
    var failureMsg = 'Dati non disponibili, riprova più tardi';

    var asyncNotify = function(msg,target) {
      if ($('.messages.error').length==0) {
        wrappedMsg = jQuery(target).prepend('<div class="messages error alert alert-danger" style="padding:20px;cursor:pointer;margin: 0;">' + msg + '</div>');
        $('.messages.error').on('click',function(){
          $(".messages.error").animate({ opacity: 0 }, 'fast', function(){
            $(".messages.error").detach();
          });
        });
      }
    }

    var clearNotifications = function(msg){
      if ($('.messages.error').length!=0) {
        jQuery("body").find('.messages.error').detach();
      }
    }

    var clickableTeams = !Drupal.settings.nonClickableTeams;
    var table = $('table.dataTarget');
    var $tableFixedColumn;
    var $tableWrapper;
    var $ajaxWrapper;

    /* classifica a2 */

    var __classifica = {
      prev_league: null,
      init : function() {

        table.detach();
        $tableFixedColumn = table.clone();
        //console.log( $tableFixedColumn.html() );

        /* kill listeners */
        $("#edit-round").off('change');
        /* new listeners */
        $(".campionato-selector .quicktabs-tabs a").on('click', $.proxy(this.get_data, this));
        $("#edit-round").on('change', $.proxy(this.get_data, this));

        this.get_data();
      },
      get_data : function(event){
        clearNotifications();
        var currentLeague = $('#quicktabs-container-campionato-selector .quicktabs-tabpage:not(.quicktabs-hide) div').data('league');
        var $round = $("#edit-round");
        var league, currentRound;
        var currentSeason = Drupal.settings.wpCurrentYear || 'x2627';
        var additional = '';

        if (this.prev_league !== currentLeague) {
          this.prev_league = currentLeague;
          league = Drupal.settings.standings.leagues[currentLeague];

          if (league) {
            $round.html('');

            $.each(league.round_options, function(id) {
              $round.append($('<option>', {
                'value': id,
                'text': this,
              }));
            });

            $round.val('ista');
          }
        }

        currentRound = $round.val();

        // Round della fase ad orologio.
        if (currentRound.indexOf('clock:') === 0) {
          additional = '&additional_league=ita2_clock&additional_round=' + currentRound.replace('clock:', '');
          currentRound = 'ista';
        }

        // League A2 con fase ad orologio attiva. La classifica istantanea deve tenere conto della fase ad orologio.
        if (!additional && currentRound === 'ista' && currentLeague.indexOf('ita2_') !== -1 && Drupal.settings.standings.a2_clock_enabled) {
          additional = '&additional_league=ita2_clock&additional_round=ista';
        }

        table.find('thead tr').children('th').eq(0).addClass('hidden-xs')
          .end().eq(13).addClass('hidden');// striscia, temporary disabled

        $tableFixedColumn
          .find('tbody tr').remove()
          .end()
          .find('thead tr').children('th').not(':first').remove().end().html('&nbsp;');

        $.get('//lnpstat.domino.it/getstatisticsfiles?task=standings&year=' + currentSeason + '&league=' + currentLeague + '&round=' + currentRound + '' + additional, function(data) {
          $('table.dataTarget tbody tr').remove();

          var colorRules = Drupal.settings.standings.color_rules;

          $.each(data, function(index, row) {
            var notes = Drupal.settings.standings.teams_with_notes[row['teamid']] || false;
            var teamname = row['teamname'] + (notes ? ' *' : '');
            var teamid = row['teamid'];
            var points = row['points'];
            var games = row['games'];
            var win = row['win'];
            var loss = row['loss'];
            var winpercent = row['winpercent'];
            var score = row['score'];
            var against = row['against'];
            //var score = row['score'];
            //var against = row['against'];
            var winhome = row['winhome'];
            var losshome = row['losshome'];
            var winaway = row['winaway'];
            var lossaway = row['lossaway'];
            var last5 = row['last5'];
            var position = row['position'];
            var rowClass = 'row-no-color';
            var $trFixedColumn;

            $.each(colorRules, function(colorRuleKey, colorRule) {
              if (position >= colorRule.standing_min && position <= colorRule.standing_max) {
                rowClass = 'row-color-' + colorRuleKey
              }
            });

            $trFixedColumn = $('<tr class="' + rowClass + '"><td>' + (clickableTeams ? '<a href="/squadra/wp/' + teamid + '">' : '') + teamname + (clickableTeams ? '</a>' : '')  + '</td></tr>');
            $tableFixedColumn.append( $trFixedColumn );

            var tr = $('<tr class="' + rowClass + '">' +
              '<td class="hidden-xs">' + (clickableTeams ? '<a href="/squadra/wp/' + teamid + '">' : '') + teamname + (clickableTeams ? '</a>' : '') + '</td>' +
              '<td>' + points + '</td>' +
              '<td>' + games + '</td>' +
              '<td>' + win + '</td>' +
              '<td>' + loss + '</td>' +
              '<td>' + winpercent + '</td>' +
              '<td>' + score + '</td>' +
              '<td>' + against + '</td>' +
              '<td>' + (score - against) + '</td>' +
              '<td>' + winhome + '</td>' +
              '<td>' + losshome + '</td>' +
              '<td>' + winaway + '</td>' +
              '<td>' + lossaway + '</td>' +
              '<td class="hidden"></td>' +// striscia, temporary disabled
              '<td>' + last5 + '</td>' +
              '</tr>');
            table.find('tbody').append(tr);
          });

          //console.log( $tableFixedColumn.html() );
          //$('.table-wrapper.ajax-wrapper').prepend( $tableFixedColumn );

          $tableWrapper = $('<div class="table-wrapper-evo"><table class="table"><tbody><tr>'+
            '<td class="table-left visible-xs"></td>'+
            '<td class="table-right"></td>'+
            '</tr></tbody></table></div>');

          $tableWrapper
            .find('.table-left').append( $tableFixedColumn )
            .end()
            .find('.table-right').append( table );

          $ajaxWrapper = $('.table-wrapper.ajax-wrapper');
          $ajaxWrapper.html( $tableWrapper );

          //$('.legenda-table').remove();
          $ajaxWrapper.append('<div class="legenda-table">' + Drupal.settings.standings.legenda + '</div>');

          $ajaxWrapper.next('.note-table').remove();
          if (Drupal.settings.standings.note[currentLeague] != undefined) {
            $ajaxWrapper.after('<div class="note-table">' + Drupal.settings.standings.note[currentLeague] + '</div>')
          }

        }).fail(function(){
          asyncNotify(failureMsg,'body');
        });
      }

    }

    function renderCalendario($table, data, currentSeason, currentLeague) {
      var clickableTeams = !Drupal.settings.nonClickableTeams;

      $table.find('tbody tr').detach();

      $.each(data, function(index, row) {
        var date = row['date'];
        var time = row['time'];
        var teamname_home = row['teamname_home'];
        var teamname_away = row['teamname_away'];
        var teamid_home = row['teamid_home'];
        var teamid_away = row['teamid_away'];
        var score_home = (row['score_home']===null) ? "0" : row['score_home'];
        var score_away = (row['score_away']===null) ? "0" : row['score_away'];
        var game_status = row['game_status'];
        var score = (game_status !== 'finished') ? '0 - 0' : '<a href="/wp/match/' + row['gameid'] + '/' + currentLeague + '/' + currentSeason + '">' + score_home + ' - ' + score_away + '</a>';
        var tabellino = (game_status !== 'finished') ? '-' : '<a href="/wp/match/' + row['gameid'] + '/' + currentLeague + '/' + currentSeason + '/tabellino">Vedi tabellino</a>';
        var arena = (row['arena']===null) ? '-' : row['arena'];
        var stream_url = row['stream_url'];

        var dataAttrDate = '';

        if (date) {
          var dateComponents = date.split('/');

          if (dateComponents.length == 3) {
            var yy = dateComponents[2];
            var mm = dateComponents[1];
            var dd = dateComponents[0];

            var hh = '0';
            var ii = '0';

            if (time) {
              var timeComponents = time.split(':');

              if (timeComponents.length == 2) {
                hh = timeComponents[0];
                ii = timeComponents[1];
              }
            }

            var matchDate = new Date(yy, mm - 1, dd, hh, ii);
            dataAttrDate = matchDate.getTime();
          }
        }

        var teamlink_home = '';
        if (teamname_home != null) {
          teamlink_home = (clickableTeams ? '<a href="/squadra/wp/' + teamid_home + '">' : '') + teamname_home + (clickableTeams ? '</a>' : '');
        }
        else {
          teamlink_home = '<a href="#"> - </a>';
        }

        var teamlink_away = '';
        if (teamname_away != null) {
          teamlink_away = (clickableTeams ? '<a href="/squadra/wp/' + teamid_away + '">' : '') + teamname_away + (clickableTeams ? '</a>' : '');
        }
        else {
          teamlink_away = '<a href="#"> - </a>';
        }

        var tr = $('<tr data-match-date="' + dataAttrDate + '" data-teamid-home="' + teamid_home + '" data-teamid-away="' + teamid_away + '">' +
          '<td>' + date + ' ' + time + '</td>' +
          '<td>' + teamlink_home + '</td>' +
          '<td>' + teamlink_away + '</td>' +
          '<td>' + score + '</td>' +
          '<td>' + tabellino + '</td>' +
          '<td>' + arena + '</td>' +
          (stream_url ? '<td class="ticket">' + LNP.streamLink(stream_url) + '</td>' : '<td></td>') +
          '</tr>');

        $table.append(tr);
      });
    }

    var __calendarioClock = {
      init : function() {
        /* kill listeners */
        $('.round-clock').off('change');
        /* new listeners */
        $('.round-clock').on('change', this.get_data);
        this.get_data()
      },
      get_data : function(){
        clearNotifications();
        var currentLeague = 'ita2_clock';
        var currentRound = $('.round-clock').val();
        var currentSeason = Drupal.settings.wpCurrentYear || 'x2627';

        $.get('//lnpstat.domino.it/getstatisticsfiles?task=schedule&year=' + currentSeason + '&league=' + currentLeague + '&round=' + currentRound + '', function(data) {
          renderCalendario($('.calendario-clock-wrapper table'), data, currentSeason, currentLeague);
        }).fail(function(){
          asyncNotify(failureMsg,'body');
        });
      }
    };

    /* calendario a2 */

    var __calendario = {
      prev_league: null,
      init : function() {
        /* kill listeners */
        $('.round-regular').off('change');
        /* new listeners */
        $(".campionato-selector .quicktabs-tabs a").on('click', $.proxy(this.get_data, this));
        $('.round-regular').on('change', $.proxy(this.get_data, this));

        this.get_data();
      },
      get_data : function(){
        clearNotifications();
        var $round = $('#edit-round');
        var currentLeague = $('#quicktabs-container-campionato-selector .quicktabs-tabpage:not(.quicktabs-hide) div').data('league');
        var league, currentRound;
        var currentSeason = Drupal.settings.wpCurrentYear || 'x2627';

        if (this.prev_league !== currentLeague) {
          this.prev_league = currentLeague;
          league = Drupal.settings.calendario[currentLeague];

          if (league) {
            $round.html('');

            $.each(league.round_options, function(id) {
              $round.append($('<option>', {
                'value': id,
                'text': this,
              }));
            });

            $round.val(league.curr_round);
          }
        }

        currentRound = $round.val();

        $.get('//lnpstat.domino.it/getstatisticsfiles?task=schedule&year=' + currentSeason + '&league=' + currentLeague + '&round=' + currentRound + '', function(data) {
          renderCalendario($('.calendario-regular-wrapper table'), data, currentSeason, currentLeague);
        }).fail(function(){
          asyncNotify(failureMsg,'body');
        });
      }
    };

    /* pagina serie A2 */

    var __serie = {
      init : function() {
        /* kill listeners */

        $("#edit-selected-campionato").off('change');
        $("#edit-round").off('change');

        $("#edit-selected-campionato--2").off('change');
        $("#edit-round--2").off('change');

        /* new listeners */

        $("#edit-selected-campionato").on('change',this.get_data);
        $("#edit-round").on('change',this.get_data);

        $("#edit-selected-campionato--2").on('change',this.get_data);
        $("#edit-round--2").on('change',this.get_data);

        this.get_data()
      },
      get_data : function(){
        clearNotifications();
        var currentLeagueStandings = $("#edit-selected-campionato").val();
        var currentLeagueSchedules = $("#edit-selected-campionato--2").val();

        var currentRound = $("#edit-round--2").val();
        var currentSeason = Drupal.settings.wpCurrentYear || 'x2627';
        var clickableTeams = !Drupal.settings.nonClickableTeams;
        var standingsAdditional = '';

        if (currentLeagueSchedules === 'ita2_clock') {
          standingsAdditional += '&additional_league=ita2_clock&additional_round=ista';
        }

        $.get('//lnpstat.domino.it/getstatisticsfiles?task=schedule&year=' + currentSeason + '&league=' + currentLeagueSchedules + '&round=' + currentRound + '', function(data) {
          $("#calendario-ajax-wrapper").contents().filter(function(){
            return (this.nodeType == 3);
          }).remove();

          if ($('table.dataTargetCal').length) {
            $('table.dataTargetCal tbody tr').detach();
          } else {
            //var emptyTable ='<div class="table-wrapper"><table class="dataTargetCal table table-striped sticky-enabled tableheader-processed sticky-table">';
            var emptyTable ='<div class="table-wrapper"><table class="dataTargetCal table table-striped">';
            emptyTable += '<thead><tr><th>Data</th><th>Casa</th><th>Ospite</th><th>Risultato</th></tr></thead>';
            emptyTable += '<tbody></tbody></table></div>';
            $('#calendario-ajax-wrapper').append(emptyTable);
          }

          $('table.dataTargetCal tbody tr').detach();
          $.each(data, function(index, row) {

            var game_date = row['date'];
            var teamname_home = row['teamname_home'];
            var teamname_away = row['teamname_away'];
            var teamid_home = row['teamid_home'];
            var teamid_away = row['teamid_away'];
            var score_home = (row['score_home']===null) ? "0" : row['score_home'];
            var score_away = (row['score_away']===null) ? "0" : row['score_away'];
            var game_status = row['game_status'];
            var score = (game_status !== 'finished') ? '0 - 0' : '<a href="/wp/match/' + row['gameid'] + '/' + currentLeagueSchedules + '/' + currentSeason + '">' + score_home + ' - ' + score_away + '</a>';

            var teamlink_home = '';
            if (teamname_home != null) {
              teamlink_home = (clickableTeams ? '<a href="/squadra/wp/' + teamid_home + '">' : '') + teamname_home + (clickableTeams ? '</a>' : '');
            }
            else {
              teamlink_home = '<a href="#"> - </a>';
            }

            var teamlink_away = '';
            if (teamname_away != null) {
              teamlink_away = (clickableTeams ? '<a href="/squadra/wp/' + teamid_away + '">' : '') + teamname_away + (clickableTeams ? '</a>' : '');
            }
            else {
              teamlink_away = '<a href="#"> - </a>';
            }

            var tr = $('<tr>' +
              '<td>'+ game_date +'</td>' +
              '<td>' + teamlink_home + '</td>' +
              '<td>' + teamlink_away + '</td>' +
              '<td>' + score + '</td>' +
              '</tr>');
            $('table.dataTargetCal').append(tr);
          });
        }).fail(function(){
          asyncNotify(failureMsg,'body');
        });

        $.get('//lnpstat.domino.it/getstatisticsfiles?task=standings&round=ista&year=' + currentSeason + '&league=' + currentLeagueStandings + standingsAdditional, function(data) {
          $("#ajax-wrapper").contents().filter(function(){
            return (this.nodeType == 3);
          }).remove();

          if ($('table.dataTargetStd').length) {
            $('table.dataTargetStd tbody tr').detach();
          } else {
            //var emptyTable ='<div class="table-wrapper"><table class="dataTargetStd table table-striped sticky-enabled tableheader-processed sticky-table">';
            var emptyTable ='<div class="table-wrapper"><table class="dataTargetStd table table-striped">';
            emptyTable += '<thead><tr><th></th><th>P</th><th>G</th><th>V</th><th>P</th><th>%</th> </tr></thead>';
            emptyTable += '<tbody></tbody></table></div>';
            $('#ajax-wrapper').append(emptyTable);
          }



          $.each(data, function(index, row) {

            var teamname = row['teamname'];
            var teamid = row['teamid'];
            var points = row['points'];
            var games = row['games'];
            var win = row['win'];
            var loss = row['loss'];
            var winpercent = row['winpercent'];
            var score = row['score'];
            var against = row['against'];
            var score = row['score'];
            var against = row['against'];
            var winhome = row['winhome'];
            var losshome = row['losshome'];
            var winaway = row['winaway'];
            var lossaway = row['lossaway'];
            var last5 = row['last5'];
            var tr = $('<tr>' +
              '<td>' + (clickableTeams ? '<a href="/squadra/wp/' + teamid + '">' : '') + teamname + (clickableTeams ? '</a>' : '') + '</td>' +
              '<td>' + points + '</td>' +
              '<td>' + games + '</td>' +
              '<td>' + win + '</td>' +
              '<td>' + loss + '</td>' +
              '<td>' + winpercent + '</td>' +
              '</tr>');
            $('table.dataTargetStd').append(tr);
          });
        }).fail(function(){
          asyncNotify(failureMsg,'body');
        });
      }

    }


    /* INIT CALLS */

    if ($('body').hasClass("page-serie-classifica")) {
      __classifica.init();
    }

    if ($('body').hasClass("page-serie-calendario")) {
      __calendario.init();
    }

    if ($('.round-clock').length > 0) {
      __calendarioClock.init();
    }

    if (($('body').hasClass("page-taxonomy-term-1")) || ($('body').hasClass("page-taxonomy-term-4"))) {
      __serie.init();
    }
  });
}(jQuery));
;
