/**
 * Created by luforn on 2018-1-4.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#quality_splitunqualified_pullrefresh',
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

mui.ready(function() {

    function isAboveZeroFloat(val) {
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)) {
            return true;
        }
        return false;
    }

    mui('.mui-content').on('change', 'input', function(){
        var iptval = this.value;
        if (iptval=='' || iptval==null){
            mui.alert('请设置每个标签的数量！');
            return ;
        }
        if (!isAboveZeroFloat(iptval)){
            mui.alert('参数设置无效，请检查每个标签的数量必须为正数！');
            return ;
        }
        var lotname = this.getAttribute('productlot');
        var lotqty = parseFloat(this.getAttribute('productqty'));
        if(parseFloat(iptval) > lotqty){
            mui.alert('批次'+lotname+'拆分的每个标签数量不可以大于批次总数！');
            return ;
        }
    });

    //确认拆分
    document.getElementById('action_dosplit').addEventListener('tap', function(){
        var wizardid = document.getElementById('quality_splitunqualified_pullrefresh').getAttribute('wizardid');
        var aasiptlist = document.body.querySelectorAll('.aas-input');
        if(aasiptlist==undefined || aasiptlist==null || aasiptlist.length<= 0){
            mui.toast('请仔细检查，可能当前不存在拆分明细！');
            return ;
        }
        var lotlines = [];
        var couldsplit = true;
        var spliterror = '';
        mui.each(aasiptlist, function(index, tempipt){
            var lineid = parseInt(tempipt.getAttribute('lineid'));
            var productlot = tempipt.getAttribute('productlot');
            var productqty = parseFloat(tempipt.getAttribute('productqty'));
            var labelqty = tempipt.value;
            if(!isAboveZeroFloat(labelqty)){
                couldsplit = false;
                spliterror = '批次'+productlot+'每标签数量必须是一个大于0的数！'
                return ;
            }else if(parseFloat(labelqty) > productqty){
                couldsplit = false;
                spliterror = '批次'+productlot+'每标签数量不能大于批次总数！'
                return ;
            }
            lotlines.push({'lineid': lineid, 'label_qty': parseFloat(labelqty)})
        });
        if(!couldsplit){
            mui.alert(spliterror);
            return ;
        }
        mui.confirm('您确认要拆分这些不合格品并重新打包？', '拆分不合格批次', ['确认', '取消'], function(e) {
            if(e.index!=0){
                return ;
            }
            action_dosplit(wizardid, lotlines);
        });
    });

    function action_dosplit(wizardid, lotlines){
        var temparams = {'wizardid': wizardid, 'lotlines': lotlines};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/quality/actiondosplit', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/quality/rejectionlist/'+dresult.orderid);
            },
            error: function (xhr, type, errorThrown) { console.log(type); }
        });
    }

});
