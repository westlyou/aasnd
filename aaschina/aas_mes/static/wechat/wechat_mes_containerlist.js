/**
 * Created by luforn on 2017-12-13.
 */


mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#container_list_pullrefresh',
        up: {
            auto: false,
            contentrefresh: '正在加载...',
            callback: pulluprefresh
        }
    }
});

function pulluprefresh() {
    mui.later(function () {
        var searchkey = document.getElementById('container_search').value;
        var pullrefresh = document.getElementById('container_list_pullrefresh');
        var containerindex = pullrefresh.getAttribute('containerindex');
        var tempparams = {'containerindex': parseInt(containerindex)};
        if (searchkey != '' && searchkey != null) {
            tempparams['searchkey'] = searchkey;
        }
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/mes/containermore', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: tempparams, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if (dresult.containercount == 0) {
                    mui('#container_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return;
                } else if (dresult.containercount < 20) {
                    mui('#container_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                } else {
                    mui('#container_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('containerindex', dresult.containerindex);
                var containerlist = document.getElementById('container_list');
                mui.each(dresult.containers, function (index, tcontainer) {
                    var li = document.createElement('li');
                    li.className = 'aas-container mui-table-view-cell';
                    li.setAttribute('containerid', tcontainer.cid);
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'> " +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-left'> " +
                                "<div class='mui-ellipsis'>  " + tcontainer.name + " </div> " +
                            "</div> " +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-center'> " +
                                "<div class='mui-ellipsis'>  " + tcontainer.alias + " </div> " +
                            "</div> " +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'> " +
                                "<div >  " + tcontainer.location + " </div> " +
                            "</div> " +
                        "</div>" +
                        "</a>";
                    containerlist.appendChild(li);
                });
            },
            error: function (xhr, type, errorThrown) {
                console.log(type);
            }
        });
    }, 1000);
}


mui.ready(function() {
    var access_url = location.href;
    var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
    mui.ajax('/aaswechat/mes/scaninit', {
        data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'access_url': access_url}, id: access_id}),
        dataType: 'json', type: 'post', timeout: 10000,
        headers: {'Content-Type': 'application/json'},
        success: function (data) {
            wx.config(data.result);
            wx.ready(function () {
            });
            wx.error(function (res) {
            });
        },
        error: function (xhr, type, errorThrown) {
            console.log(type);
        }
    });

    //容器扫描
    document.getElementById('scan_container').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描标签',
            scanType: ["qrCode"],
            success: function (result) {
                mui('#container_list_buttons').popover('toggle');
                mui.openWindow({'url': '/aaswechat/mes/containerdetail/'+result.resultStr, 'id': 'containerdetail'});
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    //容器详情页面
    mui(".mui-content").on("tap", "li.aas-container", function(){
        var containerid = this.getAttribute("containerid");
        mui.openWindow({'url': '/aaswechat/mes/containerdetail/'+containerid, 'id': 'containerdetail'});
    });


    // 搜索
    document.getElementById('container_search').addEventListener('keyup',function(event) {
        if (!event || event.keyCode != 13) {
            return;
        }
        var keyword = document.getElementById('container_search').value;
        if (keyword == null || keyword == '') {
            mui.toast('请输入请输入容器编码或者说明，搜索条件不能为空！');
            return;
        }
        var search_accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/mes/containersearch', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'searchkey': keyword}, id: search_accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                mui('#container_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                var conatainerlist = document.getElementById('container_list');
                conatainerlist.innerHTML = '';
                var dresult = data.result;
                document.getElementById('container_list_pullrefresh').setAttribute('containerindex', dresult.containerindex);
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                mui.each(dresult.containers, function(index, tcontainer){
                    var li = document.createElement('li');
                    li.className = 'aas-container mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>" +
                                "<div class='mui-ellipsis'>"+tcontainer.name+"</div>" +
                            "/div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-center'>" +
                                "<div class='mui-ellipsis'>"+tcontainer.alias+"</div>" +
                            "/div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>" +
                                "<div class='mui-ellipsis'>"+tcontainer.location+"</div>" +
                            "</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('containerid', tcontainer.cid);
                    conatainerlist.appendChild(li);
                });
            },
            error: function (xhr, type, errorThrown) {console.log(type);}
        });
    });

    //清理容器
    document.getElementById('clean_container').addEventListener('tap', function(){
        mui.alert('敬请期待！');
    });

});
