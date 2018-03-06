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

    }


});
