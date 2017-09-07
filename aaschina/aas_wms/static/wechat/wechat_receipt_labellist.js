/**
 * Created by Luforn on 2017-1-3.
 */

mui.init({swipeBack:true});

mui.ready(function(){

    //加载动画
    function aas_receipt_labellist_loading(){
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

    document.getElementById('action_add_label').addEventListener('tap', function(){
        mui('#receipt_labellist_buttons').popover('toggle');
        var receipt_labellist = document.getElementById('receipt_labellist');
        var labelul = document.createElement('ul');
        labelul.className = "mui-table-view aas-label";
        labelul.style.marginTop = '10px';
        labelul.innerHTML = "" +
            "<li class='mui-table-view-cell'>" +
                "<div class='mui-table'>" +
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>标签批次</div>" +
                    "<div class='mui-table-cell mui-col-xs-8 mui-text-right'>"+
                        "<input class='aas-lot-number' type='text' style='margin-bottom:0;height:30px;text-align: right;'/>"+
                    "</div>"+
                "</div>" +
            "</li>"+
            "<li class='mui-table-view-cell'>" +
                "<div class='mui-table'>" +
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>标签数量</div>" +
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
                        "<button type='button' class='aas-label-del mui-btn mui-btn-danger mui-btn-block mui-btn-outlined' style='padding:8px 0;'>" +
                            "<span class='mui-icon mui-icon-trash'></span>删除" +
                        "</button>" +
                    "</div>" +
                "</div>" +
            "</li>";
        receipt_labellist.appendChild(labelul);
        //更新标签个数
        var labelcountspan = document.getElementById('label_count');
        var temp_count = parseFloat(labelcountspan.getAttribute('labelcount'));
        temp_count += 1;
        labelcountspan.setAttribute('labelcount', temp_count);
        labelcountspan.innerHTML = temp_count;
    });

    //删除批次
    mui('#receipt_labellist').on('tap', 'button.aas-label-del', function(event){
        //更新标签个数
        var labelcountspan = document.getElementById('label_count');
        var temp_count = parseFloat(labelcountspan.getAttribute('labelcount'));
        temp_count -= 1;
        labelcountspan.setAttribute('labelcount', temp_count);
        labelcountspan.innerHTML = temp_count;
        //更新标签产品总数
        var labelul = this.parentNode.parentNode.parentNode.parentNode;
        var labelqtyipt = labelul.children[1].children[0].children[1].children[0];
        if (labelqtyipt.value==undefined || labelqtyipt.value==null || labelqtyipt.value==''){
            document.getElementById('receipt_labellist').removeChild(labelul);
            return ;
        }
        if (!labelqtyipt.classList.contains('aas-error')){
            var templabelspan = document.getElementById('temp_qty');
            var temp_qty = parseFloat(templabelspan.getAttribute('tempqty')) - parseFloat(labelqtyipt.value);
            templabelspan.setAttribute('tempqty', temp_qty);
            templabelspan.innerHTML = temp_qty;
        }
        document.getElementById('receipt_labellist').removeChild(labelul);
    });

    //批次名称更新
    mui('#receipt_labellist').on('change', 'input.aas-lot-number', function(event){
        var self = this;
        var lot_number = self.value;
        if (lot_number==null || lot_number==''){
            mui.toast('批次名称不能为空！');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(self.classList.contains('aas-error')){
            self.classList.remove('aas-error');
        }
    });

    //标签数量
    mui('#receipt_labellist').on('change', 'input.aas-label-qty', function(event){
        var self = this;
        var label_qty = self.value;
        if (label_qty==null || label_qty==''){
            mui.toast('标签数量不能为空！');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(!isAboveZeroFloat(label_qty) || parseFloat(label_qty)==0.0){
            mui.toast('标签数量必须是一个正数');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(self.classList.contains('aas-error')){
            self.classList.remove('aas-error');
        }

        var temp_qty = 0.0;
        var label_list = document.querySelectorAll('.aas-label-qty');
        mui.each(label_list, function(index, templabel){
            if(!templabel.classList.contains('aas-error')){
                temp_qty += parseFloat(templabel.value);
            }
        });
        var tempsapn = document.getElementById('temp_qty');
        tempsapn.innerHTML = temp_qty;
        tempsapn.setAttribute('tempqty', temp_qty);
    });

    //质保日期
    mui('#receipt_labellist').on('tap', '.aas-warranty', function(event){
        var self = this;
        var picker = new mui.DtPicker({"type":"date"});
        picker.show(function(rs) {
            self.innerHTML = rs.text;
            self.setAttribute('warranty', rs.text);
            picker.dispose();
        });
    });


    // 确认标签
    var confirm_label_flag = false;
    document.getElementById('action_confirm_labels').addEventListener('tap', function(){
        mui('#receipt_labellist_buttons').popover('toggle');
        if(confirm_label_flag){
            mui.toast('正在处理中，请不要重复操作！');
            return ;
        }
        confirm_label_flag = true;
        var aas_label_list = document.querySelectorAll('.aas-label');
        if(aas_label_list==undefined || aas_label_list.length==0){
            confirm_label_flag = false;
            mui.toast('请先添加标签明细！');
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
                confirm_label_flag = false;
                mui.toast('当前收货产品需要设置质保日期！');
                return ;
            }
        }

        var error_list = document.querySelectorAll('.aas-error');
        if(error_list!=undefined && error_list.length>0){
            confirm_label_flag = false;
            mui.toast('请仔细检查，仍有未处理的无效设置！');
            return ;
        }
        var temp_label_qty = parseFloat(document.getElementById('temp_qty').getAttribute('tempqty'));
        var product_lot_qty = parseFloat(document.getElementById('product_qty').getAttribute('productqty'));
        if(temp_label_qty != product_lot_qty){
            confirm_label_flag = false;
            mui.toast('所有标签数量总和必须和收货数量相等！');
            return ;
        }
        var label_line_list = [];
        mui.each(aas_label_list, function(index, aaslabel){
            var lot_number = aaslabel.children[0].children[0].children[1].children[0].value;
            var label_qty = parseFloat(aaslabel.children[1].children[0].children[1].children[0].value);
            var warranty_date = aaslabel.children[2].children[0].children[1].getAttribute('warranty');
            label_line_list.push({'lot_name': lot_number, 'label_qty': label_qty, 'warranty_date': warranty_date});
        });
        var wizard_id = parseInt(document.getElementById('receipt_labellist').getAttribute('wizardid'));
        var label_params = {'wizardid': wizard_id, 'label_line_list': label_line_list};
        var lot_access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var donemask = aas_receipt_labellist_loading();
        mui.ajax('/aaswechat/wms/receipt/labellistdone', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: label_params, id: lot_access_id}),
            dataType: 'json', type: 'post', timeout: 60000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                confirm_label_flag = false;
                donemask.close();
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    if(dresult.receipt_id){
                        window.location.replace('/aaswechat/wms/receiptdetail/'+dresult.receiptid);
                    }
                    return ;
                }
                window.location.replace('/aaswechat/wms/receiptdetail/'+dresult.receiptid);
            },
            error:function(xhr,type,errorThrown){
                confirm_label_flag = false;
                donemask.close();
            }
        });
    });


});
