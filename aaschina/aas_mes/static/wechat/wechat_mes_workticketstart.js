/**
 * Created by luforn on 2017-10-10.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#workticket_start_pullrefresh',
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
    function aas_start_loading(){
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

    //确认开工
    var start_flag = false;
    document.getElementById('action_start').addEventListener('tap', function(){
        if (start_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        start_flag = true;
        var workticketid = parseInt(document.getElementById('workticket_start_pullrefresh').getAttribute('workticketid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var startmask = aas_start_loading();
        mui.ajax('/aaswechat/mes/workticket/startdone', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'workticketid': workticketid}, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                start_flag = false;
                startmask.close();
                var dresult = data.result;
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/mes/workticket/finish/'+workticketid);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                start_flag = false;
                startmask.close();
            }
        });
    });

});


