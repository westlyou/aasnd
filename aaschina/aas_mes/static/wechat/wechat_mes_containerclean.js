/**
 * Created by luforn on 2017-12-13.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#container_clean_pullrefresh',
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

    var access_url = location.href;
    var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
    mui.ajax('/aaswechat/mes/scaninit', {
        data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'access_url': access_url}, id: access_id}),
        dataType: 'json', type: 'post', timeout: 10000,
        headers: {'Content-Type': 'application/json'},
        success: function (data) {
            wx.config(data.result);
            wx.ready(function () {});
            wx.error(function (res) {});
        },
        error: function (xhr, type, errorThrown) {
            console.log(type);
        }
    });

    //容器扫描
    document.getElementById('scan_container').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描容器',
            scanType: ["qrCode"],
            success: function (result) {
                mui('#container_clean_buttons').popover('toggle');
                var tempparams = {'barcode': result.resultStr};
                var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                mui.ajax('/aaswechat/mes/scancontainer', {
                    data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: tempparams, id: access_id}),
                    dataType: 'json', type: 'post', timeout: 10000,
                    headers: {'Content-Type': 'application/json'},
                    success: function (data) {
                        var dresult = data.result;
                        if(!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        initscancontainer(dresult);
                    },
                    error: function (xhr, type, errorThrown) { console.log(type);}
                });
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    function initscancontainer(data){
        var containerlist = document.getElementById('containerlist');
        var li = document.createElement('li');
        li.className = 'aas-container mui-table-view-cell mui-collapse';
        var containerhtml = "<a class='mui-navigate-right' href='#'> " +
                "<div class='mui-table'> " +
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>" +
                        "<div class='mui-ellipsis'>"+data.container_name+"</div>" +
                    "/div>"+
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-center'>" +
                        "<div class='mui-ellipsis'>"+data.container_alias+"</div>" +
                    "/div>"+
                    "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>" +
                        "<div class='mui-ellipsis'>"+data.container_location+"</div>" +
                    "</div>"+
                "</div> " +
            "</a>";
        containerhtml += "<div class='mui-collapse-content'> <ul class='mui-table-view'>";
        if (data.productlist.length > 0){
            mui.each(data.productlist, function(index, record){
                containerhtml += "<li class='mui-table-view-cell'>" +
                        "<div class='mui-table'> " +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>" +
                                "<div class='mui-ellipsis'>"+record.product_code+"</div>" +
                            "/div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-center'>" +
                                "<div class='mui-ellipsis'>"+record.product_lot+"</div>" +
                            "/div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>" +
                                "<div class='mui-ellipsis'>"+record.product_qty+"</div>" +
                            "</div>"+
                        "</div> "+
                "</li>";
            });
        }
        containerhtml += "</ul></div>";
        li.innerHTML = containerhtml;
        li.setAttribute('containerid', data.container_id);
        containerlist.appendChild(li);
    }

    //清理容器
    document.getElementById('clean_container').addEventListener('tap', function(){
        mui.confirm('确认清理以下所有容器的库存清单？', '清理容器', ['确认', '取消'], function(e) {
            if (e.index != 0) {
                return;
            }
            action_clean();
        });
    });

    function action_clean(){
        var containerlist = document.querySelectorAll('.aas-container');
        if(containerlist == undefined || containerlist == null || containerlist.length <= 0){
            mui.toast('您可能还未添加任何待清理的容器，请先扫描添加容器！');
            return ;
        }
        var containerids = [];
        mui.each(containerlist, function(index, tcontianer){
            var containerid = parseInt(tcontianer.getAttribute('containerid'));
            containerids.push(containerid);
        });
        var tempparams = {'containerids': containerids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/mes/containerclean', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: tempparams, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.reload(true);
            },
            error: function (xhr, type, errorThrown) { console.log(type);}
        });
    }



});



