/**
 * Created by luforn on 2018-1-4.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#quality_checkdetermine_pullrefresh',
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

    function isAboveZeroFloat(val){
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)){ return true; }
        return false;
    }

    mui('#aas-quality-qty').on('change', 'input', function(){
        var iptval = this.value;
        if (iptval=='' || iptval==null){
            return ;
        }
        if (!isAboveZeroFloat(iptval)){
            mui.alert('参数设置无效，请检查让步数量和不合格数量必须为正数！');
            return ;
        }
        var concession_ipt = document.getElementById('quality_concession_qty');
        var concession_qty = 0.0;
        if (concession_ipt.value!="" && concession_ipt.value!=null){
            concession_qty = parseFloat(concession_ipt.value);
        }
        var unqualified_ipt = document.getElementById('quality_unqualified_qty');
        var unqualified_qty = 0.0;
        if (unqualified_ipt.value!='' && unqualified_ipt.value!=null){
            unqualified_qty = parseFloat(unqualified_ipt.value);
        }
        var product_qty = parseFloat(document.getElementById('quality_product_qty').getAttribute('productqty'));
        var qualified_qty = product_qty - concession_qty - unqualified_qty;
        if (qualified_qty<0){
            mui.toast('参数设置错误，请仔细检查，合格数量不能小于0.0！');
            return ;
        }
        document.getElementById('quality_qualified_qty').innerHTML = qualified_qty;
    });

    //确认检测
    document.getElementById('quality_determine_done').addEventListener('tap', function(){
        mui.confirm('您确认检测判定结果？', '确认检测', ['确认', '取消'], function(e) {
            if(e.index!=0){
                return ;
            }
            action_dodetermine();
        });
    });

    function action_dodetermine(){
        var qlabelid = document.getElementById('quality_checkdetermine_pullrefresh').getAttribute('qlabelid');
        qlabelid = parseInt(qlabelid);
        var productqty = parseFloat(document.getElementById('quality_product_qty').getAttribute('productqty'));
        var concessionqty = document.getElementById('quality_concession_qty').value;
        if(concessionqty==null || concessionqty== '' || concessionqty=='0.0'){
            concessionqty = 0.0;
        }else if(!isAboveZeroFloat(concessionqty)){
            mui.toast('让步数量必须设置为一个大于0的数！');
            return ;
        }
        concessionqty = parseFloat(concessionqty);
        if(concessionqty > productqty){
            mui.toast('让步数量不能大于报检数量！');
            return ;
        }
        var unqualifiedqty = document.getElementById('quality_unqualified_qty').value;
        if(unqualifiedqty==null || unqualifiedqty== '' || unqualifiedqty=='0.0'){
            unqualifiedqty = 0.0;
        }else if(!isAboveZeroFloat(unqualifiedqty)){
            mui.toast('不合格数量必须设置为一个大于0的数！');
            return ;
        }
        unqualifiedqty = parseFloat(unqualifiedqty);
        if(unqualifiedqty > productqty){
            mui.toast('不合格数量不能大于报检数量！');
            return ;
        }
        var totalqty = concessionqty + unqualifiedqty;
        if(totalqty > productqty){
            mui.toast('不合格数量和让步数量的总和不能大于报检数量！');
            return ;
        }
        var temparams = {'qlabelid': qlabelid, 'concession_qty': concessionqty, 'unqualified_qty': unqualifiedqty};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/quality/actiondodetermine', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/quality/orderdetail/'+dresult.orderid);
            },
            error: function (xhr, type, errorThrown) { console.log(type); }
        });
    }

});