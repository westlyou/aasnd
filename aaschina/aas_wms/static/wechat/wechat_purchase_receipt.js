/**
 * Created by Luforn on 2016-11-29.
 */


mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#purchase_receipt_pullrefresh',
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

    //加载动画
    function aas_purchase_receipt_loading(){
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

    mui('#purchase_receipt_lines').on('change', 'input', function(){
        var self = this;
        var temp_qty = self.value;
        if(temp_qty==null || temp_qty==''){
            mui.toast('收货数量不能为空！');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(!isAboveZeroFloat(temp_qty)|| parseFloat(temp_qty)==0.0){
            mui.toast('收货数量设置无效，必须是一个正数！');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        var max_qty = parseFloat(self.getAttribute('productqty'));
        if(parseFloat(temp_qty)>max_qty){
            mui.toast('收货数量最多不能超过'+max_qty);
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(self.classList.contains('aas-error')){
            self.classList.remove('aas-error');
        }
    });

    mui('#purchase_receipt_lines').on('tap', '.mui-btn', function(event) {
        var li = this.parentNode.parentNode;
        mui.confirm('确认删除该条记录？', '清除上架', ['确认', '取消'], function(e) {
            if(e.index!=0){
                mui.swipeoutClose(li);
                return ;
            }
            var receipt_lines = document.getElementById('purchase_receipt_lines');
            receipt_lines.removeChild(li);
        });
    });

    var purchase_receipt_flag = false;
    document.getElementById('action_purchase_receipt').addEventListener('tap', function(){
        if(purchase_receipt_flag){
            mui.toast('采购收货正在处理中，请耐心等待！');
            return ;
        }
        purchase_receipt_flag = true;
        var error_list = document.querySelectorAll('.aas-error');
        if(error_list!=undefined && error_list.length>0){
            mui.toast('还有未处理的无效设置，请仔细检查！');
            purchase_receipt_flag = false;
            return ;
        }
        var product_list = document.querySelectorAll('.aas-purchase-ipt');
        if(product_list==undefined || product_list.length==0){
            mui.toast('当前没有可以收货的产品，您可以下拉刷新页面恢复待收货状态！');
            purchase_receipt_flag = false;
            return ;
        }
        var purchasename = document.getElementById('purchase_name').getAttribute('pname');
        var purchaseid = parseInt(document.getElementById('purchase_receipt_pullrefresh').getAttribute('purchaseid'));
        var receipt_lines = [];
        mui.each(product_list, function(index, productipt){
            receipt_lines.push({
                'product_id': parseInt(productipt.getAttribute('productid')),
                'product_qty': parseFloat(productipt.value), 'origin_order': purchasename
            });
        });
        var receipt_params = {'purchaseid': purchaseid, 'receiptlines':receipt_lines};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var purchase_receipt_mask = aas_purchase_receipt_loading();
        mui.ajax('/aaswechat/wms/purchasereceiptdone', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: receipt_params, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                purchase_receipt_flag = false;
                purchase_receipt_mask.close();
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/wms/receiptdetail/'+dresult.receiptid);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                purchase_receipt_flag = false;
                purchase_receipt_mask.close();
            }
        });
    });

});