/**
 * Created by luforn on 2017-10-10.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#workticket_finish_pullrefresh',
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

    var containerline = document.getElementById('container_line');
    var needcontainer = containerline.getAttribute('needcontainer');
    if(needcontainer=='wanted'){
        containerline.style.display = 'block';
        document.getElementById('action_scancontainer').style.display = 'block';
    }

    var printerline = document.getElementById('printer_line');
    var needprinter = printerline.getAttribute('needprinter');
    if(needprinter=='wanted'){
        printerline.style.display = 'block';
    }

    var printerid = localStorage.getItem('mesprinterid');
    var printername = localStorage.getItem('mesprintername');
    var mesprinter = document.getElementById('mes_printer');
    if(printerid==null || printername==null){
        mesprinter.setAttribute('printerid', '0');
        mesprinter.innerHTML = '单击选择打印机';
    }else{
        mesprinter.setAttribute('printerid', printerid);
        mesprinter.innerHTML = printername;
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
    function aas_finish_loading(){
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
                    localStorage.setItem('mesprinterid', items[0].value);
                    localStorage.setItem('mesprintername', items[0].text);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });

    });


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
        document.getElementById('badmode_lines').appendChild(badmodeli);
    });

    //删除不良
    mui('#badmode_lines').on('tap', 'a.mui-btn', function(event) {
        var li = this.parentNode.parentNode;
        mui.confirm('确认删除该条记录？', '清除不良模式', ['确认', '取消'], function(e) {
            if(e.index!=0){
                mui.swipeoutClose(li);
                return ;
            }
            var tempipt = li.children[1].children[1].children[1].children[0];
            var temp_qty = tempipt.value;
            if((!tempipt.classList.contains('aas-error')) && temp_qty.value!=null && temp_qty.value!=''){
                var badmodespan = document.getElementById('badmode_qty');
                var badmode_qty = parseFloat(badmodespan.getAttribute('badmodeqty'));
                badmode_qty -= parseFloat(temp_qty);
                if(badmode_qty < 0.0){
                    badmode_qty = 0.0;
                }
                badmodespan.setAttribute('badmodeqty', badmode_qty);
                badmodespan.innerHTML = badmode_qty;
            }
            var badmodediv = li.children[1].children[0].children[1];
            var badmodeid = badmodediv.getAttribute('badmodeid');
            document.getElementById('badmode_lines').removeChild(li);
            if(badmodeid=='0'){
                return ;
            }
            var badmodeul = document.getElementById('badmode_lines');
            var badmodelist = badmodeul.getAttribute('badmodelist');
            if(badmodelist==undefined || badmodelist==null || badmodelist== ''){
                return ;
            }
            var templist = [];
            mui.each(badmodelist.split(','), function(index, badmode){
                if(badmode != badmodeid){
                    templist.push(badmode);
                }
            });
            if(templist.length > 0){
                badmodelist = templist.join(',');
            }else{
                badmodelist = '';
            }
            badmodeul.setAttribute('badmodelist', badmodelist);
        });
    });

    //更新不良模式
    var loading_badmode_flag = false;
    mui('#badmode_lines').on('tap', 'div.aas-badmode-name', function(event){
        if(loading_badmode_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        loading_badmode_flag = true;
        var self = this;
        var workticketid = parseInt(document.getElementById('workticket_finish_pullrefresh').getAttribute('workticketid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var loadingmask = aas_finish_loading();
        mui.ajax('/aaswechat/mes/workticket/badmodelist', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: {'workticketid': workticketid}, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                loading_badmode_flag = false;
                loadingmask.close();
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                var oldbadmodeid = self.getAttribute('badmodeid')+'';
                var badmodepicker = new mui.PopPicker();
                badmodepicker.setData(dresult.badmodelist);
                badmodepicker.show(function(items) {
                    var badmodeul = document.getElementById('badmode_lines');
                    var badmodelist = badmodeul.getAttribute('badmodelist');
                    if (badmodelist==undefined || badmodelist==null || badmodelist==''){
                        badmodelist = items[0].value+'';
                    }else{
                        var templist = [];
                        var currentid = items[0].value;
                        var badmodes = badmodelist.split(',');
                        for(var i=0 ; i<badmodes.length; i++){
                            var tempid = badmodes[i];
                            if(tempid==currentid){
                                mui.toast('不良模式重复，请选择其他模式！');
                                return ;
                            }
                            if(tempid != oldbadmodeid){
                                templist.push(tempid);
                            }
                        }
                        templist.push(currentid);
                        badmodelist = templist.join(',');
                    }
                    self.innerText = items[0].text;
                    self.setAttribute('badmodeid', items[0].value);
                    badmodeul.setAttribute('badmodelist', badmodelist);
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
    mui('#badmode_lines').on('change', 'input.aas-badmode-qty', function(event){
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
        var badmodeqtyspan = document.getElementById('badmode_qty');
        badmodeqtyspan.innerHTML = total_badmode_qty;
        badmodeqtyspan.setAttribute('badmodeqty', total_badmode_qty);
    });

    // 生产报工
    document.getElementById('action_finish').addEventListener('tap', function(){
        mui.confirm('您确认现在就报工吗？', '生产报工', ['确认', '取消'], function(e) {
            if(e.index!=0){
                return ;
            }
            action_commit();
        });
    });

    var finish_flag = false;
    function action_commit(){
        if(finish_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        var workticketid = parseInt(document.getElementById('workticket_finish_pullrefresh').getAttribute('workticketid'));
        var params = {'workticketid': workticketid};
        var commitqty = document.getElementById('mes_commitqty').value;
        if(commitqty==undefined || commitqty==null || commitqty==''){
            mui.toast('请先输入报工数量；报工的数量中包含了不良数量！');
            return ;
        }
        if(!isAboveZeroFloat(commitqty) || parseFloat(commitqty)==0.0){
            mui.toast('报工数量必须是一个大于零的数！');
            return ;
        }
        commitqty = parseFloat(commitqty);
        var input_qty = parseFloat(document.getElementById('input_qty').getAttribute('inputqty'));
        var output_qty = parseFloat(document.getElementById('output_qty').getAttribute('outputqty'));
        if(commitqty+output_qty > input_qty){
            mui.toast('报工数量和已产出量的总数已经大于计划数量，请仔细检查！');
            return ;
        }
        params['commit_qty'] = commitqty;
        var needcontainer = document.getElementById('container_line').getAttribute('needcontainer');
        if(needcontainer == 'wanted'){
            var containerid = parseInt(document.getElementById('mes_container').getAttribute('containerid'));
            if(containerid==0){
                mui.toast('您还没有扫描容器；请先扫描容器，成品产出将直接存放在容器中！');
                return ;
            }else{
                params['container_id'] = containerid;
            }
        }
        var needprinter = document.getElementById('printer_line').getAttribute('needprinter');
        var temprinterid = parseInt(document.getElementById('mes_printer').getAttribute('printerid'));
        if(needprinter=='wanted' && temprinterid==0){
            mui.toast('您还未设置标签打印机；请先设置标签打印机，产出时将自动打印标签！');
            return ;
        }
        var badmodenamelist = document.querySelectorAll('.aas-badmode-name');
        if(badmodenamelist!=undefined && badmodenamelist.length>0){
            for(var i=0; i< badmodenamelist.length; i++){
                var badmode = badmodenamelist[i];
                if(badmode.getAttribute('badmodeid')=='0'){
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
                    mui.toast('请仔细检查有不良明细未设置不良数量！');
                    return ;
                }
            }
        }
        var error_list = document.querySelector('.aas-error');
        if(error_list!=undefined && error_list.length>0){
            mui.toast('请检查不良模式设置，有无效不良模式设置未处理！');
            return ;
        }

        var inputqty = parseFloat(document.getElementById('input_qty').getAttribute('inputqty'));
        var badmodeqty = parseFloat(document.getElementById('badmode_qty').getAttribute('badmodeqty'));
        if(badmodeqty > commitqty){
            mui.toast('不良数量的总和不能大于报工数量，请仔细检查！');
            return ;
        }
        finish_flag = true;
        var badmodelist = document.querySelectorAll('.aas-badmode');
        if(badmodelist!=undefined && badmodelist.length>0){
            var badmode_lines = [];
            mui.each(badmodelist, function(index, templi){
                var badmode_id = parseInt(templi.children[1].children[0].children[1].getAttribute('badmodeid'));
                var badmode_qty = parseFloat(templi.children[1].children[1].children[1].children[0].value);
                badmode_lines.push({'badmode_id': badmode_id, 'badmode_qty': badmode_qty});
            });
            params['badmode_lines'] = badmode_lines;
        }
        var equipmentid = parseInt(document.getElementById('wequipment').getAttribute('equipmentid'));
        if(equipmentid > 0){
            params['equipment_id'] = equipmentid;
        }
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var finishmask = aas_finish_loading();
        mui.ajax('/aaswechat/mes/workticket/docommit',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id }),
            dataType:'json', type:'post', timeout:30000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                finish_flag = false;
                finishmask.close();
                var dresult = data.result;
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if(needprinter=='wanted' && dresult.labelid!='0' && dresult.labelid!=0){
                    autoprintlabel(temprinterid, [dresult.labelid]);
                }else{
                    window.location.replace('/aaswechat/mes');
                }
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                finish_flag = false;
                finishmask.close();
            }
        });
    }

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



    //扫描容器
    document.getElementById('action_scancontainer').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描容器',
            scanType: ["qrCode"],
            success: function (result) {
                var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                var barcode = result.resultStr;
                mui.ajax('/aaswechat/mes/workticket/scancontainer',{
                    data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'barcode': barcode}, id: access_id }),
                    dataType:'json', type:'post', timeout:10000,
                    headers:{'Content-Type':'application/json'},
                    success:function(data){
                        var dresult = data.result;
                        if (!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        var mescontainer = document.getElementById('mes_container');
                        mescontainer.setAttribute('containerid', dresult.container_id);
                        mescontainer.innerHTML = dresult.container_name;
                    },
                    error:function(xhr,type,errorThrown){ console.log(type);}
                });
            },
            fail: function (result) {mui.toast(result.errMsg);}
        });
    });

    //切换设备
    document.getElementById('wequipment').addEventListener('tap', function(){
        var workstationid = parseInt(document.getElementById('workstation').getAttribute('workstationid'));
        if(workstationid==0){
            mui.toast('请仔细检查是否设置了工位信息！');
            return ;
        }
        var worktocketid = parseInt(document.getElementById('workticket_finish_pullrefresh').getAttribute('workticketid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/mes/workticket/equipmentlist',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'workticketid': worktocketid}, id: access_id }),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if (dresult.equipments.length<=0){
                    mui.alert('当前工位可能还未设置设备信息！');
                    return ;
                }
                var eqpicker = new mui.PopPicker();
                eqpicker.setData(dresult.equipments);
                eqpicker.show(function(items) {
                    var wequipment = document.getElementById('wequipment');
                    wequipment.innerText = items[0].text;
                    wequipment.setAttribute('equipmentid', items[0].value);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });

});
