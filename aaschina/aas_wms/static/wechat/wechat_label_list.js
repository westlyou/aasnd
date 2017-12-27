/**
 * Created by Luforn on 2016-11-9.
 */


mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#label_list_pullrefresh',
        up: {
            auto: false,
            contentrefresh: '正在加载...',
            callback: pulluprefresh
        }
    }
});

function pulluprefresh(){
    mui.later(function(){
        var searchkey = document.getElementById('label_search').value;
        var pullrefresh = document.getElementById('label_list_pullrefresh');
        var labelindex = pullrefresh.getAttribute('labelindex');
        var label_params = {'labelindex': parseInt(labelindex)};
        if(searchkey!=''&&searchkey!=null){
            label_params['searchkey'] = searchkey;
        }
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/labelmore', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: label_params, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if (dresult.labelcount==0){
                    mui('#label_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.labelcount<20){
                    mui('#label_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#label_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('labelindex', dresult.labelindex);
                var label_list = document.body.querySelector('#label_list');
                mui.each(dresult.labels, function(index, label){
                    var li = document.createElement('li');
                    li.className = 'aas-label mui-table-view-cell';
                    li.setAttribute('labelid', label.label_id);
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                            "<div class='mui-table'> " +
                                "<div class='mui-table-cell mui-col-xs-8 mui-text-left'> " +
                                    "<div class='mui-ellipsis'>  "+label.product_code+" </div> " +
                                    "<div class='mui-ellipsis'>  "+label.product_lot+" </div> " +
                                "</div> " +
                                "<div class='mui-table-cell mui-col-xs-4 mui-text-right'> " +
                                    "<div >  "+label.location_name+" </div> " +
                                    "<div >  "+label.product_qty+" </div> " +
                                "</div> " +
                            "</div>"+
                        "</a>";
                    label_list.appendChild(li);
                });
            },
            error: function (xhr, type, errorThrown) { console.log(type); }
        });
    }, 1000);
}

mui.ready(function(){
    var access_url = location.href;
    var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
    mui.ajax('/aaswechat/wms/scaninit',{
        data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'access_url': access_url}, id: access_id }),
        dataType:'json', type:'post', timeout:10000,
        headers:{'Content-Type':'application/json'},
        success:function(data){
            wx.config(data.result);
            wx.ready(function(){});
            wx.error(function(res){});
        },
        error:function(xhr,type,errorThrown){ console.log(type); }
    });

    mui('.mui-popover-bottom').on('tap', '#scan_label', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描标签',
            scanType: ["qrCode"],
            success: function (result) {
                mui('#label_list_buttons').popover('toggle');
                mui.openWindow({'url': '/aaswechat/wms/labeldetail/'+result.resultStr, 'id': 'labeldetail'});
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    mui('.mui-popover-bottom').on('tap', '#merge_label', function(){
        mui('#label_list_buttons').popover('toggle');
        mui.openWindow({'url': '/aaswechat/wms/labelmerge', 'id': 'labelmerge'});
    });

    mui(".mui-content").on("tap", "li.aas-label", function(){
        var labelid = this.getAttribute("labelid");
        mui.openWindow({'url': '/aaswechat/wms/labeldetail/'+labelid, 'id': 'labeldetail'});
    });

    // 搜索
    document.getElementById('label_search').addEventListener('keyup',function(event) {
        if (!event || event.keyCode != 13) {
            return;
        }
        var keyword = document.getElementById('label_search').value;
        if (keyword == null || keyword == '') {
            mui.toast('请输入请输入产品编码或者批次，搜索条件不能为空！');
            return;
        }
        var search_accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/labelsearch', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'searchkey': keyword}, id: search_accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                mui('#label_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                var label_list = document.getElementById('label_list');
                label_list.innerHTML = '';
                var dresult = data.result;
                document.getElementById('label_list_pullrefresh').setAttribute('labelindex', dresult.labelindex);
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                mui.each(dresult.labels, function(index, lline){
                    var li = document.createElement('li');
                    li.className = 'aas-label mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>" +
                                "<div class='mui-ellipsis'>"+lline.product_code+"</div>" +
                                "<div class='mui-ellipsis'>"+lline.product_lot+"</div><" +
                            "/div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>" +
                                "<div class='mui-ellipsis'>"+lline.location_name+"</div>" +
                                "<div class='mui-ellipsis'>"+lline.product_qty+"</div><" +
                            "</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('labelid', lline.label_id);
                    label_list.appendChild(li);
                });
            },
            error: function (xhr, type, errorThrown) {console.log(type);}
        });
    });


});