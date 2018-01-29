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
                if(dresult.tips!=undefined && dresult.tips!=''){
                    mui.toast(dresult.tips);
                }
                var mwmaterialli = document.getElementById(dresult.mwmterialid);
                if(mwmaterialli!=undefined && mwmaterialli!=null){
                    mwmaterialli.parentNode.removeChild(mwmaterialli);
                }
                var feedline = document.createElement('li');
                feedline.className = 'mui-table-view-cell';
                feedline.setAttribute('id', dresult.mwmterialid);
                feedline.setAttribute('mwmaterialid', dresult.mwmaterialid);
                feedline.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;font-size:12px;' href='javascript:;'>" +
                    "<div class='mui-table'>" +
                        "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+dresult.material_code+"</div>" +
                        "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+dresult.material_qty+"</div>" +
                    "</div>";
                var scanbtn = document.getElementById('workstation_'+dresult.workstation_id+'_scanbtn');
                var workstationul = scanbtn.parentNode;
                if(workstationul.lastChild == scanbtn){
                    workstationul.appendChild(feedline);
                }else{
                    workstationul.insertBefore(feedline, scanbtn.nextSibling);
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
                if(dresult.tips!=undefined && dresult.tips!=''){
                    mui.toast(dresult.tips);
                }
                var mwmaterialli = document.getElementById(dresult.mwmterialid);
                if(mwmaterialli!=undefined && mwmaterialli!=null){
                    mwmaterialli.parentNode.removeChild(mwmaterialli);
                }
                var feedline = document.createElement('li');
                feedline.className = 'mui-table-view-cell';
                feedline.setAttribute('id', dresult.mwmterialid);
                feedline.setAttribute('mwmaterialid', dresult.mwmaterialid);
                feedline.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;font-size:12px;' href='javascript:;'>" +
                    "<div class='mui-table'>" +
                        "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+dresult.material_code+"</div>" +
                        "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+dresult.material_qty+"</div>" +
                    "</div>";
                var scanbtn = document.getElementById('workstation_'+dresult.workstation_id+'_scanbtn');
                var workstationul = scanbtn.parentNode;
                if(workstationul.lastChild == scanbtn){
                    workstationul.appendChild(feedline);
                }else{
                    workstationul.insertBefore(feedline, scanbtn.nextSibling);
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
        var mwmaterialid = this.getAttribute('mwmaterialid');
        mui.openWindow({'url': '/aaswechat/mes/feeding/materialdetail/'+mwmaterialid, 'id': 'feedingdetail'});
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
