/* ===========================================================
# bootstrap-tour - v0.5.0
# http://bootstraptour.com
# ==============================================================
# Copyright 2012-2013 Ulrich Sossou
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
*/
!function(){!function(a,b){var c,d;return d=b.document,c=function(){function c(b){this._options=a.extend({name:"tour",container:"body",keyboard:!0,useLocalStorage:!1,debug:!1,backdrop:!1,redirect:!0,basePath:"",template:"<div class='popover tour'>          <div class='arrow'></div>          <h3 class='popover-title'></h3>          <div class='popover-content'></div>          <div class='popover-navigation'>            <button class='btn' data-role='prev'>&laquo; Prev</button>            <span data-role='separator'>|</span>            <button class='btn' data-role='next'>Next &raquo;</button>            <button class='btn' data-role='end'>End tour</button>          </div>        </div>",afterSetState:function(){},afterGetState:function(){},afterRemoveState:function(){},onStart:function(){},onEnd:function(){},onShow:function(){},onShown:function(){},onHide:function(){},onHidden:function(){},onNext:function(){},onPrev:function(){}},b),this._options.useLocalStorage||a.cookie||this._debug("jQuery.cookie is not loaded."),this._steps=[],this.setCurrentStep(),this.backdrop={overlay:null,step:null,background:null}}return c.prototype.setState=function(c,d){return c=""+this._options.name+"_"+c,this._options.useLocalStorage?b.localStorage.setItem(c,d):a.cookie(c,d,{expires:36500,path:"/"}),this._options.afterSetState(c,d)},c.prototype.removeState=function(c){return c=""+this._options.name+"_"+c,this._options.useLocalStorage?b.localStorage.removeItem(c):a.removeCookie(c,{path:"/"}),this._options.afterRemoveState(c)},c.prototype.getState=function(c){var d;return d=this._options.useLocalStorage?b.localStorage.getItem(""+this._options.name+"_"+c):a.cookie(""+this._options.name+"_"+c),(void 0===d||"null"===d)&&(d=null),this._options.afterGetState(c,d),d},c.prototype.addSteps=function(a){var b,c,d,e;for(e=[],c=0,d=a.length;d>c;c++)b=a[c],e.push(this.addStep(b));return e},c.prototype.addStep=function(a){return this._steps.push(a)},c.prototype.getStep=function(b){return null!=this._steps[b]?a.extend({id:"step-"+b,path:"",placement:"right",title:"",content:"<p></p>",next:b===this._steps.length-1?-1:b+1,prev:b-1,animation:!0,container:this._options.container,backdrop:this._options.backdrop,redirect:this._options.redirect,template:this._options.template,onShow:this._options.onShow,onShown:this._options.onShown,onHide:this._options.onHide,onHidden:this._options.onHidden,onNext:this._options.onNext,onPrev:this._options.onPrev},this._steps[b]):void 0},c.prototype.start=function(b){var c,e=this;return null==b&&(b=!1),this.ended()&&!b?this._debug("Tour ended, start prevented."):(a(d).off("click.bootstrap-tour",".popover *[data-role=next]").on("click.bootstrap-tour",".popover *[data-role=next]",function(a){return a.preventDefault(),e.next()}),a(d).off("click.bootstrap-tour",".popover *[data-role=prev]").on("click.bootstrap-tour",".popover *[data-role=prev]",function(a){return a.preventDefault(),e.prev()}),a(d).off("click.bootstrap-tour",".popover *[data-role=end]").on("click.bootstrap-tour",".popover *[data-role=end]",function(a){return a.preventDefault(),e.end()}),this._onresize(function(){return e.showStep(e._current)}),this._setupKeyboardNavigation(),c=this._makePromise(null!=this._options.onStart?this._options.onStart(this):void 0),this._callOnPromiseDone(c,this.showStep,this._current))},c.prototype.next=function(){var a;return a=this.hideStep(this._current),this._callOnPromiseDone(a,this.showNextStep)},c.prototype.prev=function(){var a;return a=this.hideStep(this._current),this._callOnPromiseDone(a,this.showPrevStep)},c.prototype.end=function(){var c,e,f=this;return c=function(){return a(d).off("click.bootstrap-tour"),a(d).off("keyup.bootstrap-tour"),a(b).off("resize.bootstrap-tour"),f.setState("end","yes"),f._hideBackdrop(),null!=f._options.onEnd?f._options.onEnd(f):void 0},e=this.hideStep(this._current),this._callOnPromiseDone(e,c)},c.prototype.ended=function(){return!!this.getState("end")},c.prototype.restart=function(){return this.removeState("current_step"),this.removeState("end"),this.setCurrentStep(0),this.start()},c.prototype.hideStep=function(b){var c,d,e,f=this;return e=this.getStep(b),d=this._makePromise(null!=e.onHide?e.onHide(this):void 0),c=function(){var b;return b=a(e.element).popover("hide"),e.reflex&&b.css("cursor","").off("click.bootstrap-tour"),e.backdrop&&f._hideBackdrop(),null!=e.onHidden?e.onHidden(f):void 0},this._callOnPromiseDone(d,c),d},c.prototype.showStep=function(b){var c,e,f,g=this;return(f=this.getStep(b))?(c=this._makePromise(null!=f.onShow?f.onShow(this):void 0),e=function(){var c,e;return g.setCurrentStep(b),e=a.isFunction(f.path)?f.path.call():g._options.basePath+f.path,c=[d.location.pathname,d.location.hash].join(""),g._isRedirect(e,c)?(g._redirect(f,e),void 0):null!=f.element&&0!==a(f.element).length&&a(f.element).is(":visible")?(f.backdrop&&g._showBackdrop(f.element),g._showPopover(f,b),null!=f.onShown&&f.onShown(g),g._debug("Step "+(g._current+1)+" of "+g._steps.length)):(g._debug("Skip the step "+(g._current+1)+". The element does not exist or is not visible."),g.showNextStep(),void 0)},this._callOnPromiseDone(c,e)):void 0},c.prototype.setCurrentStep=function(a){return null!=a?(this._current=a,this.setState("current_step",a)):(this._current=this.getState("current_step"),this._current=null===this._current?0:parseInt(this._current))},c.prototype.showNextStep=function(){var a,b,c,d=this;return c=this.getStep(this._current),b=function(){return d.showStep(c.next)},a=this._makePromise(null!=c.onNext?c.onNext(this):void 0),this._callOnPromiseDone(a,b)},c.prototype.showPrevStep=function(){var a,b,c,d=this;return c=this.getStep(this._current),b=function(){return d.showStep(c.prev)},a=this._makePromise(null!=c.onPrev?c.onPrev(this):void 0),this._callOnPromiseDone(a,b)},c.prototype._debug=function(a){return this._options.debug?b.console.log("Bootstrap Tour '"+this._options.name+"' | "+a):void 0},c.prototype._isRedirect=function(a,b){return null!=a&&""!==a&&a.replace(/\?.*$/,"").replace(/\/?$/,"")!==b.replace(/\/?$/,"")},c.prototype._redirect=function(b,c){return a.isFunction(b.redirect)?b.redirect.call(this,c):b.redirect===!0?(this._debug("Redirect to "+c),d.location.href=c):void 0},c.prototype._renderNavigation=function(b,c){var d;return d=a.isFunction(b.template)?a(b.template(c,b)):a(b.template),b.prev>=0||d.find(".popover-navigation *[data-role=prev]").remove(),b.next>=0||d.find(".popover-navigation *[data-role=next]").remove(),b.prev>=0&&b.next>=0||d.find(".popover-navigation *[data-role=separator]").remove(),d.clone().wrap("<div>").parent().html()},c.prototype._showPopover=function(b,c){var d,e,f,g,h=this;return f=a.extend({},this._options),b.options&&a.extend(f,b.options),b.reflex&&a(b.element).css("cursor","pointer").on("click.bootstrap-tour",function(){return h.next()}),g=this._renderNavigation(b,c,f),d=a(b.element),d.data("popover")&&d.popover("destroy"),d.popover({placement:b.placement,trigger:"manual",title:b.title,content:b.content,html:!0,animation:b.animation,container:b.container,template:g,selector:b.element}).popover("show"),e=a(b.element).data("popover").tip(),e.attr("id",b.id),this._reposition(e,b),this._scrollIntoView(e)},c.prototype._reposition=function(b,c){var e,f,g,h,i,j,k;if(i=b[0].offsetWidth,h=b[0].offsetHeight,k=b.offset(),g=k.left,j=k.top,e=a(d).outerHeight()-k.top-a(b).outerHeight(),0>e&&(k.top=k.top+e),f=a("html").outerWidth()-k.left-a(b).outerWidth(),0>f&&(k.left=k.left+f),k.top<0&&(k.top=0),k.left<0&&(k.left=0),b.offset(k),"bottom"===c.placement||"top"===c.placement){if(g!==k.left)return this._replaceArrow(b,2*(k.left-g),i,"left")}else if(j!==k.top)return this._replaceArrow(b,2*(k.top-j),h,"top")},c.prototype._replaceArrow=function(a,b,c,d){return a.find(".arrow").css(d,b?50*(1-b/c)+"%":"")},c.prototype._scrollIntoView=function(c){var d;return d=c.get(0).getBoundingClientRect(),d.top>=0&&d.bottom<a(b).height()&&d.left>=0&&d.right<a(b).width()?void 0:c.get(0).scrollIntoView(!0)},c.prototype._onresize=function(c,d){return a(b).on("resize.bootstrap-tour",function(){return clearTimeout(d),d=setTimeout(c,100)})},c.prototype._setupKeyboardNavigation=function(){var b=this;return this._options.keyboard?a(d).on("keyup.bootstrap-tour",function(a){if(a.which)switch(a.which){case 39:return a.preventDefault(),b._current<b._steps.length-1?b.next():b.end();case 37:if(a.preventDefault(),b._current>0)return b.prev();break;case 27:return a.preventDefault(),b.end()}}):void 0},c.prototype._makePromise=function(b){return b&&a.isFunction(b.then)?b:null},c.prototype._callOnPromiseDone=function(a,b,c){var d=this;return a?a.then(function(){return b.call(d,c)}):b.call(this,c)},c.prototype._showBackdrop=function(a){return null===this.backdrop.overlay?(this._showOverlay(),this._showOverlayElement(a)):void 0},c.prototype._hideBackdrop=function(){return null!==this.backdrop.overlay?(this._hideOverlayElement(),this._hideOverlay()):void 0},c.prototype._showOverlay=function(){return this.backdrop=a("<div/>"),this.backdrop.addClass("tour-backdrop"),this.backdrop.height(a(d).innerHeight()),a("body").append(this.backdrop)},c.prototype._hideOverlay=function(){return this.backdrop.remove(),this.backdrop.overlay=null},c.prototype._showOverlayElement=function(b){var c,d,e,f;return f=a(b),e=5,d=f.offset(),d.top=d.top-e,d.left=d.left-e,c=a("<div/>"),c.width(f.innerWidth()+e).height(f.innerHeight()+e).addClass("tour-step-background").offset(d),f.addClass("tour-step-backdrop"),a("body").append(c),this.backdrop.step=f,this.backdrop.background=c},c.prototype._hideOverlayElement=function(){return this.backdrop.step.removeClass("tour-step-backdrop"),this.backdrop.background.remove(),this.backdrop.step=null,this.backdrop.background=null},c}(),b.Tour=c}(jQuery,window)}.call(this);