/**
 * Created by luforn on 2018-1-14.
 */


mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#linefeeding_materialdetail_pullrefresh',
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

mui.ready(function(){});
