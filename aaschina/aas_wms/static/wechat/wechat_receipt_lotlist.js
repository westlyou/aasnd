/**
 * Created by Luforn on 2016-12-30.
 */


mui.init({swipeBack:true});

mui.ready(function(){

    //加载动画
    function aas_receipt_lotlist_loading(){
        var receiptmask = mui.createMask();
        var loadimg = document.createElement('img'), maskEl = receiptmask[0];
        maskEl.removeEventListener('tap', arguments.callee);
        loadimg.setAttribute('src', '/aas_base/static/wechat/aas/images/loading.gif');
        loadimg.setAttribute('width', '50px');
        loadimg.setAttribute('height', '50px');
        loadimg.setAttribute('alt', '加载中.........');
        loadimg.setAttribute('style', "position:fixed;top:50%;left:50%;margin:-25px 0 0 -25px;");
        maskEl.appendChild(loadimg);
        receiptmask.show();
        return receiptmask;
    }

    function isAboveZeroFloat(val){
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)){ return true; }
        return false;
    }

    document.getElementById('action_add_lot').addEventListener('tap', function(){
        mui('#receipt_lotlist_buttons').popover('toggle');
        var receipt_lotlist = document.getElementById('receipt_lotlist');
        var lotul = document.createElement('ul');
        lotul.className = "mui-table-view aas-lot";
        lotul.style.marginTop = '10px';
        lotul.innerHTML = "" +
            "<li class='mui-table-view-cell'>" +
                "<div class='mui-table'>" +
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>批次名称</div>" +
                    "<div class='mui-table-cell mui-col-xs-8 mui-text-right'>"+
                        "<input class='aas-lot-number' type='text' style='margin-bottom:0;height:30px;text-align: right;'/>"+
                    "</div>"+
                "</div>" +
            "</li>"+
            "<li class='mui-table-view-cell'>" +
                "<div class='mui-table'>" +
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>批次数量</div>" +
                    "<div class='mui-table-cell mui-col-xs-8 mui-text-right'>"+
                        "<input class='aas-lot-qty' type='text' style='margin-bottom:0;height:30px;text-align: right;'/>"+
                    "</div>"+
                "</div>" +
            "</li>"+
            "<li class='mui-table-view-cell'>" +
                "<div class='mui-table'>" +
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>每包数量</div>" +
                    "<div class='mui-table-cell mui-col-xs-8 mui-text-right'>"+
                        "<input class='aas-label-qty' type='text' style='margin-bottom:0;height:30px;text-align: right;'/>"+
                    "</div>"+
                "</div>" +
            "</li>"+
            "<li class='mui-table-view-cell'>" +
                "<div class='mui-table'>" +
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>质保日期</div>" +
                    "<div class='aas-warranty mui-table-cell mui-col-xs-8 mui-text-right' warranty=''></div>"+
                "</div>" +
            "</li>"+
            "<li class='mui-table-view-cell'>" +
                "<div class='mui-table'>" +
                    "<div class='mui-table-cell mui-col-xs-12 mui-text-center'>" +
                        "<button type='button' class='aas-lot-del mui-btn mui-btn-danger mui-btn-block mui-btn-outlined' style='padding:8px 0;'>" +
                            "<span class='mui-icon mui-icon-trash'></span>删除" +
                        "</button>" +
                    "</div>" +
                "</div>" +
            "</li>";
        receipt_lotlist.appendChild(lotul);
    });

    //删除批次
    mui('#receipt_lotlist').on('tap', 'button.aas-lot-del', function(event){
        var lotul = this.parentNode.parentNode.parentNode.parentNode;
        var lotqtyipt= lotul.children[1].children[0].children[1].children[0];
        if (lotqtyipt.value==undefined || lotqtyipt.value==null || lotqtyipt.value==''){
            document.getElementById('receipt_lotlist').removeChild(lotul);
            return ;
        }
        if (!lotqtyipt.classList.contains('aas-error')){
            var templotspan = document.getElementById('temp_qty');
            var temp_qty = parseFloat(templotspan.getAttribute('tempqty')) - parseFloat(lotqtyipt.value);
            templotspan.setAttribute('tempqty', temp_qty);
            templotspan.innerHTML = temp_qty;
        }
        document.getElementById('receipt_lotlist').removeChild(lotul);
    });

    //批次名称更新
    mui('#receipt_lotlist').on('change', 'input.aas-lot-number', function(event){
        var self = this;
        var lot_number = self.value;
        if (lot_number==null || lot_number==''){
            mui.toast('批次名称不能为空！');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        var lot_number_count = 0;
        var lot_number_list = document.querySelectorAll('.aas-lot-number');
        for(var i=0;i < lot_number_list.length; i++){
            var temp_lot_number = lot_number_list[i];
            if (temp_lot_number.value == lot_number){
                lot_number_count += 1;
            }
            if(lot_number_count > 1){
                break;
            }
        }
        if (lot_number_count>1){
            mui.toast("批次名称："+lot_number+"有重复，请修改！");
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(self.classList.contains('aas-error')){
            self.classList.remove('aas-error');
        }
    });

    //批次数量
    mui('#receipt_lotlist').on('change', 'input.aas-lot-qty', function(event){
        var self = this;
        var lot_qty = self.value;
        if (lot_qty==null || lot_qty==''){
            mui.toast('批次数量不能为空！');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(!isAboveZeroFloat(lot_qty) || parseFloat(lot_qty)==0.0){
            mui.toast('批次数量必须是一个正数');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        lot_qty = parseFloat(lot_qty);
        var label_qty_line = self.parentNode.parentNode.parentNode.nextSibling;
        var label_qty_ipt = label_qty_line.firstChild.lastChild.firstChild;
        if(!label_qty_ipt.classList.contains('aas-error')){
            if(parseFloat(label_qty_ipt.value) > lot_qty){
                label_qty_ipt.value = lot_qty;
            }
        }
        if(self.classList.contains('aas-error')){
            self.classList.remove('aas-error');
        }
        var temp_qty = 0.0;
        var lot_list = document.querySelectorAll('.aas-lot-qty');
        mui.each(lot_list, function(index, templot){
            if (!templot.classList.contains('aas-error')){
                temp_qty += parseFloat(templot.value);
            }
        });
        var lotspan = document.getElementById('temp_qty');
        lotspan.setAttribute('tempqty', temp_qty);
        lotspan.innerHTML = temp_qty;
    });

    //包装数量
    mui('#receipt_lotlist').on('change', 'input.aas-label-qty', function(event){
        var self = this;
        var label_qty = self.value;
        if (label_qty==null || label_qty==''){
            mui.toast('包装数量不能为空！');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(!isAboveZeroFloat(label_qty) || parseFloat(label_qty)==0.0){
            mui.toast('包装数量必须是一个正数');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        // 包装数量不能大于批次数量
        label_qty = parseFloat(label_qty);
        var lot_qty_line = self.parentNode.parentNode.parentNode.previousSibling;
        var lot_qty_ipt = lot_qty_line.firstChild.lastChild.firstChild;
        if(!lot_qty_ipt.classList.contains('aas-error')){
            if(parseFloat(lot_qty_ipt.value) < label_qty){
                self.value = lot_qty_ipt.value;
            }
        }
        if(self.classList.contains('aas-error')){
            self.classList.remove('aas-error');
        }
    });

    //质保日期
    mui('#receipt_lotlist').on('tap', '.aas-warranty', function(event){
        var self = this;
        var picker = new mui.DtPicker({"type":"date"});
        picker.show(function(rs) {
            self.innerHTML = rs.text;
            self.setAttribute('warranty', rs.text);
            picker.dispose();
        });
    });

    // 确认批次拆分
    var confirm_lot_flag = false;
    document.getElementById('action_confirm_lots').addEventListener('tap', function(){
        mui('#receipt_lotlist_buttons').popover('toggle');
        if(confirm_lot_flag){
            mui.toast('正在处理中，请不要重复操作！');
            return ;
        }
        confirm_lot_flag = true;
        var aas_lot_list = document.querySelectorAll('.aas-lot');
        if(aas_lot_list==undefined || aas_lot_list.length==0){
            confirm_lot_flag = false;
            mui.toast('请先添加批次明细！');
            return ;
        }
        mui.each(document.querySelectorAll('input'),function(index, ipt){
            if((ipt.value==null || ipt.value=='') && ipt.type != 'hidden'){
                if(!ipt.classList.contains('aas-error')){
                    ipt.classList.add('aas-error');
                }
            }
        });
        // 必须添加质保日期验证
        if (document.getElementById('need_warranty').value == '1'){
            var warrantyflag = true;
            mui.each(document.querySelectorAll('.aas-warranty'), function(index, twarranty){
                var warranty_date = twarranty.getAttribute('warranty');
                if(warranty_date=='' || warranty_date==null){
                    warrantyflag = false;
                }
            });
            if(!warrantyflag){
                confirm_lot_flag = false;
                mui.toast('当前收货产品需要设置质保日期！');
                return ;
            }
        }
        var error_list = document.querySelectorAll('.aas-error');
        if(error_list!=undefined && error_list.length>0){
            confirm_lot_flag = false;
            mui.toast('请仔细检查，仍有未处理的无效设置！');
            return ;
        }
        var temp_lot_qty = parseFloat(document.getElementById('temp_qty').getAttribute('tempqty'));
        var product_lot_qty = parseFloat(document.getElementById('product_qty').getAttribute('productqty'));
        if(temp_lot_qty != product_lot_qty){
            confirm_lot_flag = false;
            mui.toast('所有批次数量总和必须和收货数量相等！');
            return ;
        }
        var lot_line_list = [];
        mui.each(aas_lot_list, function(index, aaslot){
            var lot_number = aaslot.children[0].children[0].children[1].children[0].value;
            var lot_qty = parseFloat(aaslot.children[1].children[0].children[1].children[0].value);
            var label_qty = parseFloat(aaslot.children[2].children[0].children[1].children[0].value);
            var warranty_date = aaslot.children[3].children[0].children[1].getAttribute('warranty');
            var lotvals = {'lot_name': lot_number, 'lot_qty': lot_qty, 'label_qty': label_qty};
            if (warranty_date!='' && warranty_date!=null){
                lotvals['warranty_date'] = warranty_date;
            }
            lot_line_list.push(lotvals);
        });
        var line_id = parseInt(document.getElementById('receipt_lotlist').getAttribute('lineid'));
        var lot_params = {'lineid': line_id, 'lot_line_list': lot_line_list};
        var lot_access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var donemask = aas_receipt_lotlist_loading();
        mui.ajax('/aaswechat/wms/receipt/lotlistdone', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: lot_params, id: lot_access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                confirm_lot_flag = false;
                donemask.close();
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/wms/receipt/labellist/'+dresult.receiptwizardid);
            },
            error:function(xhr,type,errorThrown){
                confirm_lot_flag = false;
                donemask.close();
            }
        });
    });

});
