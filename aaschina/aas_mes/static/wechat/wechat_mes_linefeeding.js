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

    var feeding_flag = false;
    mui('div.mui-scroll').on('tap', 'button.aas-feeding', function(event){
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
                var workstationid = parseInt(self.getAttribute('workstationid'));
                var barcode = result.resultStr;
                var prefix = barcode.substring(0,2);
                if(prefix=='AT'){
                    action_scancontainer(barcode, workstationid);
                }else{
                    action_scanlabel(barcode, workstationid);
                }
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    //标签上料
    function action_scanlabel(barcode, workstationid){
        var scanparams = {'barcode': barcode, 'workstationid': workstationid};
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
                var feedline = document.createElement('li');
                feedline.className = 'mui-table-view-cell';
                feedline.setAttribute('id', 'feeding_'+dresult.feeding_id);
                feedline.setAttribute('feedingid', dresult.feeding_id);
                feedline.innerHTML = "<div class='mui-slider-right mui-disabled'> <a class='mui-btn mui-btn-red aas-feeding-del'>删除</a> </div> " +
                    "<div class='mui-slider-handle'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>"+dresult.material_code+"</div>" +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-center'>"+dresult.material_lot+"</div>" +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+dresult.material_qty+"</div>" +
                        "</div>" +
                    "</div>";
                document.getElementById('workstation_'+workstationid).appendChild(feedline);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                feeding_flag = false;
                scanmask.close();
            }
        });
    }

    //容器上料
    function action_scancontainer(barcode, workstationid){
        var scanparams = {'barcode': barcode, 'workstationid': workstationid};
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
                if(dresult.materiallist.length <= 0){
                    return ;
                }
                mui.each(dresult.materiallist, function(index, tmaterial){
                    var feedline = document.createElement('li');
                    feedline.className = 'mui-table-view-cell';
                    feedline.setAttribute('id', 'feeding_'+tmaterial.feeding_id);
                    feedline.setAttribute('feedingid', tmaterial.feeding_id);
                    feedline.innerHTML = "<div class='mui-slider-right mui-disabled'> <a class='mui-btn mui-btn-red aas-feeding-del'>删除</a> </div> " +
                        "<div class='mui-slider-handle'>" +
                            "<div class='mui-table'>" +
                                "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>"+tmaterial.material_code+"</div>" +
                                "<div class='mui-table-cell mui-col-xs-4 mui-text-center'>"+tmaterial.material_lot+"</div>" +
                                "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+tmaterial.material_qty+"</div>" +
                            "</div>" +
                        "</div>";
                    document.getElementById('workstation_'+workstationid).appendChild(feedline);
                });
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                feeding_flag = false;
                scanmask.close();
            }
        });
    }



    //删除上料记录
    var feeding_delete_flag = false;
    mui('.mui-content').on('tap', '.aas-feeding-del', function(event) {
        if(feeding_delete_flag){
            mui.toast('删除操作正在处理，请耐心等待！');
            return ;
        }
        feeding_delete_flag = true;
        var feedingli = this.parentNode.parentNode;
        mui.confirm('确认删除该条记录？', '清除上料记录', ['确认', '取消'], function(e) {
            if(e.index!=0){
                feeding_delete_flag = false;
                mui.swipeoutClose(feedingli);
                return ;
            }
            var feeding_id = parseInt(feedingli.getAttribute('feedingid'));
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var feeding_delmask = aas_feeding_loading();
            mui.ajax('/aaswechat/mes/feeding/materialdel',{
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'feeding_id': feeding_id}, id: access_id }),
                dataType:'json', type:'post', timeout:30000,
                headers:{'Content-Type':'application/json'},
                success:function(data){
                    var dresult = data.result;
                    feeding_delete_flag = false;
                    feeding_delmask.close();
                    if (!dresult.success){
                        mui.toast(dresult.message);
                        return ;
                    }
                    feedingli.parentNode.removeChild(feedingli);
                },
                error:function(xhr,type,errorThrown){
                    console.log(type);
                    feeding_delete_flag = false;
                    feeding_delmask.close();
                }
            });
        });
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
