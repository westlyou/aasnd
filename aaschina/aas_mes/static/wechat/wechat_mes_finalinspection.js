/**
 * Created by luforn on 2018-6-7.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#finalinspection_pullrefresh',
        down : {
          height:50,
          auto: false,
          contentdown : "下拉可以刷新",
          contentover : "释放立即刷新",
          contentrefresh : "正在刷新...",
          callback : function(){ mui.later(function(){ window.location.reload(true); }, 1000); }
        }
    }
});


mui.ready(function(){

    var finalprinter = localStorage.getItem('finalinspectionprinter');
    if(finalprinter!=null && finalprinter!=''){
        var printer = JSON.parse(finalprinter);
        var printerspan = document.getElementById('mes_printer');
        printerspan.setAttribute('printerid', printer.printer_id);
        printerspan.innerHTML = printer.printer_name;
    }

    mui.ajax('/aaswechat/mes/scaninit',{
        data: JSON.stringify({
            jsonrpc: "2.0", method: 'call', params: {'access_url': location.href}, id: Math.floor(Math.random() * 1000 * 1000 * 1000)
        }),
        dataType:'json', type:'post', timeout:10000,
        headers:{'Content-Type':'application/json'},
        success:function(data){
            wx.config(data.result);
            wx.ready(function(){});
            wx.error(function(res){});
        },
        error:function(xhr,type,errorThrown){ console.log(type); }
    });


    //加载动画
    function aas_final_loading(){
        var tempmask = mui.createMask();
        var loadimg = document.createElement('img'), maskEl = tempmask[0];
        maskEl.removeEventListener('tap', arguments.callee);
        loadimg.setAttribute('src', '/aas_base/static/wechat/aas/images/loading.gif');
        loadimg.setAttribute('width', '50px');
        loadimg.setAttribute('height', '50px');
        loadimg.setAttribute('alt', '加载中.........');
        loadimg.setAttribute('style', "position:fixed;top:50%;left:50%;margin:-25px 0 0 -25px;");
        maskEl.appendChild(loadimg);
        tempmask.show();
        return tempmask;
    }

    function isAboveZeroFloat(val){
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)){ return true; }
        return false;
    }

    //添加不良模式
    document.getElementById('action_addbadmode').addEventListener('tap', function(){
        var badmodeli = document.createElement('li');
        badmodeli.className = "mui-table-view-cell aas-badmode";
        badmodeli.innerHTML = "<div class='mui-slider-right mui-disabled'><a class='mui-btn mui-btn-red'>删除</a></div>" +
            "<div class='mui-slider-handle'>" +
                "<div class='mui-table'> " +
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>不良模式</div>" +
                    "<div class='mui-table-cell mui-col-xs-8 mui-text-right aas-badmode-name' badmodeid='0'>单击选择不良模式</div>" +
                "</div>" +
                "<div class='mui-table'> " +
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>不良数量</div>" +
                    "<div class='mui-table-cell mui-col-xs-8 mui-text-right'>" +
                        "<input class='aas-badmode-qty' type='text' style='margin-bottom:0;height:30px;text-align: right;'/>" +
                    "</div>" +
                "</div>" +
            "</div>";
        document.getElementById('badmodelist').appendChild(badmodeli);
    });

    //删除不良
    mui('#badmodelist').on('tap', 'a.mui-btn', function(event) {
        var li = this.parentNode.parentNode;
        mui.confirm('确认删除该条记录？', '清除不良模式', ['确认', '取消'], function(e) {
            if(e.index!=0){
                mui.swipeoutClose(li);
                return ;
            }
            var tempipt = li.children[1].children[1].children[1].children[0];
            var temp_qty = tempipt.value;
            if((!tempipt.classList.contains('aas-error')) && temp_qty.value!=null && temp_qty.value!=''){
                var badmodespan = document.getElementById('mes_badmode');
                var badmode_qty = parseFloat(badmodespan.getAttribute('qty'));
                badmode_qty -= parseFloat(temp_qty);
                if(badmode_qty < 0.0){
                    badmode_qty = 0.0;
                }
                badmodespan.setAttribute('qty', badmode_qty);
                badmodespan.innerHTML = badmode_qty;
            }
            document.getElementById('badmodelist').removeChild(li);
        });
    });

    //更新不良模式
    var loading_badmode_flag = false;
    mui('#badmodelist').on('tap', 'div.aas-badmode-name', function(event){
        if(loading_badmode_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        loading_badmode_flag = true;
        var self = this;
        var meslineid = parseInt(document.getElementById('badmodelist').getAttribute('meslineid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var loadingmask = aas_final_loading();
        mui.ajax('/aaswechat/mesline/badmodelist', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: {'meslineid': meslineid}, id: access_id}),
            dataType: 'json', type: 'post', timeout: 30000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                loading_badmode_flag = false;
                loadingmask.close();
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                var badmodepicker = new mui.PopPicker();
                badmodepicker.setData(dresult.badmodelist);
                badmodepicker.show(function(items) {
                    self.innerText = items[0].text;
                    self.setAttribute('badmodeid', items[0].value);
                });
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                loading_badmode_flag = false;
                loadingmask.close();
            }
        });
    });

    //编辑不良数量
    mui('#badmodelist').on('change', 'input.aas-badmode-qty', function(event){
        var self = this;
        var badmode_qty = self.value;
        if(badmode_qty==null || badmode_qty==''){
            mui.toast('不良数量不能为空！');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(!isAboveZeroFloat(badmode_qty) || parseFloat(badmode_qty)==0.0){
            mui.toast('不良数量必须是一个正数');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(self.classList.contains('aas-error')){
            self.classList.remove('aas-error');
        }
        var badmode_list = document.querySelectorAll('.aas-badmode-qty');
        var total_badmode_qty = 0.0;
        mui.each(badmode_list, function(index, badmode){
            var tempqty = badmode.value;
            if((!badmode.classList.contains('aas-error')) && tempqty!=null && tempqty!=''){
                total_badmode_qty += parseFloat(tempqty);
            }
        });
        var mesbadmode = document.getElementById('mes_badmode');
        mesbadmode.setAttribute('qty', total_badmode_qty);
        mesbadmode.innerHTML = total_badmode_qty;
        var product_qty = parseFloat(document.getElementById('mes_qty').getAttribute('qty'));
        if(total_badmode_qty > product_qty){
            mui.toast('不良数量不能超过检测数量！');
            return ;
        }
        var badmodeqtyspan = document.getElementById('mes_badmode');
        badmodeqtyspan.innerHTML = total_badmode_qty;
        badmodeqtyspan.setAttribute('qty', total_badmode_qty);
    });


    //单击选择打印机
    document.getElementById('mes_printer').addEventListener('tap', function(){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/labelprinters', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: {}, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if (dresult.printers.length<=0){
                    mui.alert('请联系管理员，可能系统中还未配置打印机！');
                    return ;
                }
                var printerpicker = new mui.PopPicker();
                printerpicker.setData(dresult.printers);
                printerpicker.show(function(items) {
                    var labelprinter = document.getElementById('mes_printer');
                    labelprinter.innerText = items[0].text;
                    labelprinter.setAttribute('printerid', items[0].value);
                    var printerstr = JSON.stringify({'printer_id': items[0].value, 'printer_name': items[0].text});
                    localStorage.setItem('finalinspectionprinter', printerstr);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });

    });


    //确认提交终检
    var donebtn = document.getElementById('action_done');
    document.getElementById('action_done').addEventListener('tap', function(){
        var doing = parseInt(donebtn.getAttribute('doing'));
        if(doing == 1){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        var labelid = parseInt(document.getElementById('mes_label').getAttribute('labelid'));
        var printerid = parseInt(document.getElementById('mes_printer').getAttribute('printerid'));
        if(labelid>0 && printerid==0){
            donebtn.setAttribute('doing', '0');
            mui.toast('请先设置好标签打印机！');
            return ;
        }
        var badmodelist = document.querySelectorAll('.aas-badmode');
        if(badmodelist==undefined || badmodelist==null || badmodelist.length<=0){
            donebtn.setAttribute('doing', '0');
            mui.toast('请先添加不良模式信息！');
            return ;
        }
        var badmodenamelist = document.querySelectorAll('.aas-badmode-name');
        if(badmodenamelist!=undefined && badmodenamelist.length>0){
            for(var i=0; i< badmodenamelist.length; i++){
                var badmode = badmodenamelist[i];
                if(badmode.getAttribute('badmodeid')=='0'){
                    donebtn.setAttribute('doing', '0');
                    mui.toast('请仔细检查有不良明细未设置不良模式！');
                    return ;
                }
            }
        }
        var badmode_qty_list = document.querySelectorAll('.aas-badmode-qty');
        if(badmode_qty_list!=undefined && badmode_qty_list.length>0){
            for(var i=0; i< badmode_qty_list.length; i++){
                var badmode_qty = badmode_qty_list[i];
                if(!badmode_qty.classList.contains('aas-error') && (badmode_qty.value==null || badmode_qty.value=='')){
                    badmode_qty.classList.add('aas-error');
                    donebtn.setAttribute('doing', '0');
                    mui.toast('请仔细检查有不良明细未设置不良数量！');
                    return ;
                }
            }
        }
        var error_list = document.querySelector('.aas-error');
        if(error_list!=undefined && error_list.length>0){
            donebtn.setAttribute('doing', '0');
            mui.toast('请检查不良模式设置，有无效不良模式设置未处理！');
            return ;
        }
        var productqty = parseFloat(document.getElementById('mes_qty').getAttribute('qty'));
        var badmodeqty = parseFloat(document.getElementById('mes_badmode').getAttribute('qty'));
        if(badmodeqty > productqty){
            donebtn.setAttribute('doing', '0');
            mui.toast('不良数量不能超过检测数量！');
            return ;
        }
        var employeeid = parseInt(document.getElementById('mes_employee').getAttribute('employeeid'));
        if(employeeid==0){
            donebtn.setAttribute('doing', '0');
            mui.toast('请先扫描终检员工条码！');
            return ;
        }
        var workorderid = parseInt(document.getElementById('mes_workorder').getAttribute('workorderid'));
        var containerid = parseInt(document.getElementById('mes_container').getAttribute('containerid'));
        var temparams = {
            'workorderid': workorderid, 'employeeid': employeeid, 'labelid': labelid, 'containerid': containerid
        };
        var badmode_lines = [];
        mui.each(badmodelist, function(index, templi){
            var badmode_id = parseInt(templi.children[1].children[0].children[1].getAttribute('badmodeid'));
            var badmode_qty = parseFloat(templi.children[1].children[1].children[1].children[0].value);
            badmode_lines.push({'badmode_id': badmode_id, 'badmode_qty': badmode_qty});
        });
        temparams['badmodelines'] = badmode_lines;
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        donebtn.setAttribute('doing', '1');
        var finalmask = aas_final_loading();
        mui.ajax('/aaswechat/mes/finalinspection/done',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id }),
            dataType:'json', type:'post', timeout:30000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                finalmask.close();
                donebtn.setAttribute('doing', '0');
                var dresult = data.result;
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if(labelid > 0){
                    autoprintlabel(printerid, [labelid]);
                }else{
                    window.location.replace('/aaswechat/mes');
                }
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                finalmask.close();
                donebtn.setAttribute('doing', '0');
            }
        });
    });



    //自动打印标签
    function autoprintlabel(printerid, labelids){
        mui.toast('正在打印标签，请稍后......');
        var printparams = {'printerid': printerid, 'labelids': labelids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/mes/printlabels', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: printparams, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                var records = dresult.records;
                if(records.length<=0){
                    window.location.replace('/aaswechat/mes');
                    return ;
                }
                var printer = dresult.printer;
                var printurl = 'http://'+dresult.printurl;
                mui.each(records, function(index, record){
                    var params = {'label_name': printer, 'label_count': 1, 'label_content':record};
                    $.ajax({type:'post', dataType:'script', url: printurl, data: params,
                        success: function (result) {
                            window.location.replace('/aaswechat/mes');
                        },
                        error:function(XMLHttpRequest,textStatus,errorThrown){}
                    });
                });
            },
            error: function (xhr, type, errorThrown) { console.log(type);}
        });
    }

    //扫描员工
    document.getElementById('action_scanemployee').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '员工扫描',
            scanType: ["qrCode"],
            success: function (result) {
                var temparams = {'barcode': result.resultStr};
                var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                mui.ajax('/aaswechat/mes/finalinspection/scanemployee', {
                    data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
                    dataType: 'json', type: 'post', timeout: 10000,
                    headers: {'Content-Type': 'application/json'},
                    success: function (data) {
                        var dresult = data.result;
                        if(!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        var mesemployee = document.getElementById('mes_employee');
                        mesemployee.setAttribute('employeeid', dresult.eid);
                        mesemployee.innerHTML = dresult.ename;
                    },
                    error: function (xhr, type, errorThrown) { console.log(type);}
                });
            },
            fail: function (result) {mui.toast(result.errMsg);}
        });
    });


});