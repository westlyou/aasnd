/**
 * Created by luforn on 2018-3-6.
 */

mui.init({ swipeBack:true });

mui.ready(function(){

    document.getElementById('action_pass').addEventListener('tap', function(){
        mui.confirm('您确认按照当前待检标签OK？', '出货检测', ['是', '否'], function(e) {
            if (e.index == 0) {
                dochecking(true);
            }
        });
    });


    document.getElementById('action_fail').addEventListener('tap', function(){
        mui.confirm('您确认按照当前待检标签NG？', '出货检测', ['是', '否'], function(e) {
            if (e.index == 0) {
                dochecking(false);
            }
        });
    });

    function dochecking(pass){
        var oqclabelid = parseInt(document.getElementById('oqcchecking_pullrefresh').getAttribute('oqclabelid'));
        var temparams = {'oqclabelid': oqclabelid, 'qualified': pass};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/quality/oqcchecking/dochecking', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/quality');
            },
            error: function (xhr, type, errorThrown) { console.log(type); }
        });

    }


});
