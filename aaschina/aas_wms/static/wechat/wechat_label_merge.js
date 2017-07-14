/**
 * Created by Luforn on 2016-11-11.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#label_merge_pullrefresh',
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
    function aas_label_merge_loading(){
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

    var scan_location_flag = false;
    mui('.mui-popover-bottom').on('tap', '#scan_location', function(){
        mui('#label_merge_buttons').popover('toggle');
        if(scan_location_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        scan_location_flag = true;
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描库位',
            scanType: ["qrCode"],
            success: function (result) {
                var label_location_mask = aas_label_merge_loading();
                var scan_access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                mui.ajax('/aaswechat/wms/labelmergelocation', {
                    data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'barcode': result.resultStr}, id: scan_access_id }),
                    dataType:'json', type:'post', timeout:10000,
                    headers:{'Content-Type':'application/json'},
                    success:function(data){
                        var dresult = data.result;
                        scan_location_flag = false;
                        label_location_mask.close();
                        if (!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        var labellocation = document.getElementById('label_location');
                        labellocation.setAttribute('locationid', dresult.location_id);
                        labellocation.innerHTML = dresult.location_name;
                    },
                    error:function(xhr,type,errorThrown){
                        console.log(type);
                        scan_location_flag = false;
                        label_location_mask.close();
                    }
                });
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    var scan_label_flag = false;
    mui('.mui-popover-bottom').on('tap', '#scan_label', function(){
        mui('#label_merge_buttons').popover('toggle');
        if(scan_label_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        scan_label_flag = true;
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描标签',
            scanType: ["qrCode"],
            success: function (result) {
                var label_label_mask = aas_label_merge_loading();
                var scan_access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                mui.ajax('/aaswechat/wms/labelmergelabel', {
                    data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'barcode': result.resultStr}, id: scan_access_id }),
                    dataType:'json', type:'post', timeout:10000,
                    headers:{'Content-Type':'application/json'},
                    success:function(data){
                        var dresult = data.result;
                        scan_label_flag = false;
                        label_label_mask.close();
                        if (!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        var labelline = document.getElementById('#label_'+dresult.label_id);
                        if(labelline!=null && labelline!=undefined){
                            mui.toast('标签已存在，请不要重复扫描！');
                            return ;
                        }
                        var mergeproduct = document.getElementById('product_code');
                        var productid = parseInt(mergeproduct.getAttribute('productid'));
                        if(productid==0){
                            mergeproduct.setAttribute('productid', dresult.product_id);
                            mergeproduct.innerHTML = dresult.product_code;
                        }else if(productid!=dresult.product_id){
                            mui.toast('当前标签与已经添加的标签产品不同不能合并！');
                            return ;
                        }
                        var mergelot = document.getElementById('product_lot');
                        var lotid = parseInt(mergelot.getAttribute('lotid'));
                        if(lotid==0){
                            mergelot.setAttribute('lotid', dresult.lot_id);
                            mergelot.innerHTML = dresult.lot_name;
                        }else if(lotid!=dresult.lot_id){
                            mui.toast('当前标签与已经添加的标签批次不同不能合并！');
                            return ;
                        }
                        var mergeqty = document.getElementById('product_qty');
                        var product_qty = parseFloat(mergeqty.getAttribute('productqty'));
                        var totalqty = product_qty+dresult.product_qty;
                        mergeqty.setAttribute('productqty', totalqty);
                        mergeqty.innerHTML = totalqty;

                        var templine = document.createElement('li');
                        templine.setAttribute('id', 'label_'+dresult.label_id);
                        templine.setAttribute('labelid', dresult.label_id);
                        templine.setAttribute('labelqty', dresult.product_qty);
                        templine.className = "aas-label mui-table-view-cell";
                        templine.innerHTML = "<div class='mui-slider-right mui-disabled'> <a href='javascript:;' class='mui-btn mui-btn-red'>删除</a> </div>"+
                            "<div class='mui-slider-handle'> " +
                                "<div class='mui-table'>" +
                                    "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+dresult.product_code+"</div>" +
                                    "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+dresult.product_qty+"</div>" +
                                "</div>" +
                                "<div class='mui-table'>" +
                                    "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+dresult.location_name+"</div>" +
                                    "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+dresult.label_name+"</div>" +
                                "</div>" +
                            "</div>";
                        document.getElementById('label_lines').appendChild(templine);
                    },
                    error:function(xhr,type,errorThrown){
                        console.log(type);
                        scan_label_flag = false;
                        label_label_mask.close();
                    }
                });
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    mui('#label_lines').on('tap', '.mui-btn', function(event) {
        var elem = this;
        var templi = elem.parentNode.parentNode;
        mui.confirm('确认删除该条记录？', '清除标签', ['确认', '取消'], function(e) {
            if (e.index == 0) {
                var tempqty = document.getElementById('product_qty');
                var balanceqty = parseFloat(tempqty.getAttribute('productqty')) - parseFloat(templi.getAttribute('labelqty'));
                tempqty.setAttribute('productqty', balanceqty);
                tempqty.innerHTML = balanceqty;
                templi.parentNode.removeChild(li);
                var labellines = document.body.querySelectorAll('.aas-label');
                if (labellines==undefined || labellines==null){
                    var mergeproduct  = document.getElementById('product_code');
                    mergeproduct.setAttribute('productid', 0);
                    mergeproduct.innerHTML = '';
                    var mergelot = document.getElementById('product_lot');
                    mergelot.setAttribute('lotid', 0);
                    mergelot.innerHTML = '';
                }
            } else {
                mui.swipeoutClose(li);
            }
        });
    });

    var label_merge_flag = false;
    mui('.mui-popover-bottom').on('tap', '#action_merge', function(){
        mui('#label_merge_buttons').popover('toggle');
        if(label_merge_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        label_merge_flag = true;
        var labellocationid  = document.getElementById('label_location').getAttribute('locationid');
        if(labellocationid=='0'){
            mui.toast('目标库位未设置，请扫描新标签物品即将放置的库位！');
            label_merge_flag = false;
            return ;
        }
        var labellines = document.body.querySelectorAll('.aas-label');
        if (labellines==undefined || labellines==null || labellines.length<=0){
            mui.toast('请先添加需要合并的标签，再执行此操作！');
            label_merge_flag = false;
            return ;
        }
        mui.confirm('确认执行合并？', '标签合并', ['确认', '取消'], function(e) {
            if (e.index != 0) { return ; }
            var label_ids = [];
            mui.each(labellines, function(index, lline){
                label_ids.push(parseInt(lline.getAttribute('labelid')));
            });
            var merge_params = {'locationid': parseInt(label_location), 'labelids': label_ids};
            var merge_access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var merge_mask = aas_label_merge_loading();
            mui.ajax('/aaswechat/wms/labelmergedone', {
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: merge_params, id: merge_access_id }),
                dataType:'json', type:'post', timeout:10000,
                headers:{'Content-Type':'application/json'},
                success:function(data){
                    var dresult = data.result;
                    label_merge_flag = false;
                    merge_mask.close();
                    if (!dresult.success){
                        mui.toast(dresult.message);
                        return ;
                    }
                    window.location.replace('/aaswechat/wms/labeldetail/'+dresult.labelid);
                },
                error:function(xhr,type,errorThrown){
                    console.log(type);
                    label_merge_flag = false;
                    merge_mask.close();
                }
            });
        });

    });

});
