/**
 * Created by luforn on 2017-7-10.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#delivery_line_list_pullrefresh',
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
        var pullrefresh = document.getElementById('delivery_line_list_pullrefresh');
        var lineindex = pullrefresh.getAttribute('lineindex');
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var params = {'lineindex': parseInt(lineindex)};
        var keyword = document.getElementById('product_code_search').value;
        if(keyword!=null && keyword!=''){
            params['product_code'] = keyword;
        }
        mui.ajax('/aaswechat/wms/deliverylinemore',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: accessid}),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                if (dresult.linecount==0){
                    mui('#delivery_line_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.linecount<20){
                    mui('#delivery_line_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#delivery_line_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('lineindex', dresult.lineindex);
                var delivery_line_list = document.getElementById('delivery_line_list');
                mui.each(dresult.deliverylines, function(index, dline){
                    var li = document.createElement('li');
                    li.className = 'aas-delivery-line mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>"+dline.product_code+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+dline.delivery_type+"</div>"+
                        "</div>"+
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>"+dline.delivery_name+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+dline.product_qty+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('deliverylineid', dline.line_id);
                    delivery_line_list.appendChild(li);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }, 1000);
}

mui.ready(function(){

    mui(".mui-content").on("tap", "li.aas-delivery-line", function(){
        var deliverylineid = this.getAttribute("deliverylineid");
        mui.openWindow({'url': '/aaswechat/wms/deliveryline/'+deliverylineid, 'id': 'deliveryline'});
    });

    document.getElementById('product_code_search').addEventListener('keyup',function(event) {
        if (!event || event.keyCode != 13) {
            return;
        }
        var keyword = document.getElementById('product_code_search').value;
        if (keyword == null || keyword == '') {
            mui.toast('请输入产品编码，产品编码不能为空！');
            return;
        }
        var search_accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/deliverylinesearch', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'product_code': keyword}, id: search_accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                mui('#delivery_line_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                var delivery_line_list = document.getElementById('delivery_line_list');
                delivery_line_list.innerHTML = '';
                var titleli = document.createElement('li');
                titleli.className = 'mui-table-view-cell';
                titleli.innerHTML = "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>产品编码</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>发货类型</div>"+
                        "</div>"+
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>发货单号</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>待发数量</div>"+
                        "</div>";
                delivery_line_list.appendChild(titleli);
                var dresult = data.result;
                document.getElementById('delivery_line_list_pullrefresh').setAttribute('lineindex', dresult.lineindex);
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                mui.each(dresult.deliverylines, function(index, dline){
                    var li = document.createElement('li');
                    li.className = 'aas-delivery-line mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>"+dline.product_code+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+dline.delivery_type+"</div>"+
                        "</div>"+
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>"+dline.delivery_name+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+dline.product_qty+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('deliverylineid', dline.line_id);
                    delivery_line_list.appendChild(li);
                });
            },
            error: function (xhr, type, errorThrown) {console.log(type);}
        });
    });

});