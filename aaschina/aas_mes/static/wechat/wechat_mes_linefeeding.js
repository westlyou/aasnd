/**
 * Created by luforn on 2017-10-9.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#linefeeding_pullrefresh',
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

    mui.ajax('/aaswechat/mes/scaninit',{
        data: JSON.stringify({
            jsonrpc: "2.0", method: 'call', params: {'access_url': location.href}, id: Math.floor(Math.random() * 1000 * 1000 * 1000)
        }),
        dataType:'json', type:'post', timeout:10000,
        headers:{'Content-Type':'application/json'},
        success:function(data){
            wx.config(data.result);
            wx.ready(function(){});
            wx.error(function(res){});
        },
        error:function(xhr,type,errorThrown){ console.log(type); }
    });

    //加载动画
    function aas_feeding_loading(){
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

    //单击扫描上料按钮
    var feeding_flag = false;
    document.getElementById('action_scan').addEventListener('tap', function(){
        if (feeding_flag){
            mui.toast('上料操作正在执行，请耐心等待！');
            return ;
        }
        feeding_flag = true;
        var self = this;
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描上料',
            scanType: ["qrCode"],
            success: function (result) {
                var barcode = result.resultStr;
                var prefix = barcode.substring(0,2);
                if(prefix=='AT'){
                    action_scancontainer(barcode);
                }else{
                    action_scanlabel(barcode);
                }
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    //标签上料
    function action_scanlabel(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var scanmask = aas_feeding_loading();
        mui.ajax('/aaswechat/mes/feeding/materialscan',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id }),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                feeding_flag = false;
                scanmask.close();
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if(dresult.tips!=undefined && dresult.tips!=''){
                    mui.toast(dresult.tips);
                }
                var materialli = document.getElementById(dresult.tmaterial_id);
                if(materialli!=undefined && materialli!=null){
                    materialli.parentNode.removeChild(materialli);
                }
                var feedline = document.createElement('li');
                feedline.className = 'mui-table-view-cell';
                feedline.setAttribute('id', dresult.tmaterial_id);
                feedline.setAttribute('material_id', dresult.material_id);
                feedline.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;font-size:12px;' href='javascript:;'>" +
                    "<div class='mui-table'>" +
                        "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+dresult.material_code+"</div>" +
                        "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+dresult.material_qty+"</div>" +
                    "</div>";
                var feedinglist = document.getElementById('feedinglist');
                var feedchildren = feedinglist.children;
                if(feedchildren==null || feedchildren.length<=0){
                    feedinglist.appendChild(feedline);
                }else{
                    feedinglist.insertBefore(feedline, feedinglist.children[0]);
                }
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                feeding_flag = false;
                scanmask.close();
            }
        });
    }

    //容器上料
    function action_scancontainer(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var scanmask = aas_feeding_loading();
        mui.ajax('/aaswechat/mes/feeding/containerscan',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id }),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                feeding_flag = false;
                scanmask.close();
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if(dresult.tips!=undefined && dresult.tips!=''){
                    mui.toast(dresult.tips);
                }
                var materialli = document.getElementById(dresult.tmaterial_id);
                if(materialli!=undefined && materialli!=null){
                    materialli.parentNode.removeChild(materialli);
                }
                var feedline = document.createElement('li');
                feedline.className = 'mui-table-view-cell';
                feedline.setAttribute('id', dresult.tmaterial_id);
                feedline.setAttribute('materialid', dresult.material_id);
                feedline.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;font-size:12px;' href='javascript:;'>" +
                    "<div class='mui-table'>" +
                        "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+dresult.material_code+"</div>" +
                        "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+dresult.material_qty+"</div>" +
                    "</div>";
                var feedinglist = document.getElementById('feedinglist');
                var feedchildren = feedinglist.children;
                if(feedchildren==null || feedchildren.length<=0){
                    feedinglist.appendChild(feedline);
                }else{
                    feedinglist.insertBefore(feedline, feedinglist.children[0]);
                }
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                feeding_flag = false;
                scanmask.close();
            }
        });
    }


    //查看上料详情
    mui('div.mui-scroll').on('tap', 'li.aas-material', function(event){
        var materialid = this.getAttribute('materialid');
        var meslineid = document.getElementById('linefeeding_pullrefresh').getAttribute('meslineid');
        mui.openWindow({'url': '/aaswechat/mes/feeding/materialdetail/'+meslineid+'/'+materialid, 'id': 'feedingdetail'});
    });


    //刷新上料库存信息
    var feeding_refresh_flag = false;
    document.getElementById('action_refresh_stock').addEventListener('tap', function(){
        if(feeding_refresh_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        feeding_refresh_flag = true;
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var meslineid = parseInt(document.getElementById('linefeeding_pullrefresh').getAttribute('meslineid'));
        var tempparams = {'meslineid': meslineid};
        var feeding_refreshmask = aas_feeding_loading();
        mui.ajax('/aaswechat/mes/feeding/refreshstock',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: tempparams, id: access_id }),
            dataType:'json', type:'post', timeout:30000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                feeding_refresh_flag = false;
                feeding_refreshmask.close();
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                feeding_refresh_flag = false;
                feeding_refreshmask.close();
            }
        });
    });

});
