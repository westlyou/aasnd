/**
 * Created by luforn on 2017-7-29.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#inventory_list_pullrefresh',
        up: {
            auto: false,
            contentrefresh: '正在加载...',
            callback: pulluprefresh
        },
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

function pulluprefresh(){
    mui.later(function(){
        var pullrefresh = document.body.querySelector('#inventory_list_pullrefresh');
        var inventoryindex = pullrefresh.getAttribute('inventoryindex');
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var params = {'inventoryindex': parseInt(inventoryindex)};
        mui.ajax('/aaswechat/wms/inventorymore',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: accessid}),
            dataType:'json', type:'post', timeout:20000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                if (dresult.inventorycount==0){
                    mui('#inventory_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.inventorycount<20){
                    mui('#inventory_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#inventory_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('inventoryindex', dresult.inventoryindex);
                var inventory_list = document.getElementById('inventory_list');
                mui.each(dresult.inventorylist, function(index, tinventory){
                    var li = document.createElement('li');
                    li.className = 'aas-inventory mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-12 mui-text-left'>"+tinventory.inventory_name+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('inventoryid', tinventory.inventory_id);
                    inventory_list.appendChild(li);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }, 1000);
}

mui.ready(function(){

    mui(".mui-content").on("tap", "li.aas-inventory", function(){
        var inventoryid = this.getAttribute("inventoryid");
        mui.openWindow({'url': '/aaswechat/wms/inventory/'+inventoryid, 'id': 'inventorydetail'});
    });

});