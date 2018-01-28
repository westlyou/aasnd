/**
 * Created by Luforn on 2018-01-28.
 */

mui.init({ swipeBack:true });

mui.ready(function(){

    //加载动画
    function aas_label_split_loading(){
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

    function isAboveZeroInteger(val){
        var reg = /^[1-9]\d*$/;
        if(reg.test(val)){ return true; }
        return false;
    }

    function isAboveZeroFloat(val){
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)){ return true; }
        return false;
    }

    document.getElementById('split_label_qty').addEventListener('change', function(){
        var self = this;
        var product_qty = parseFloat(document.getElementById('product_label_qty').getAttribute('qty'));
        var label_qty = document.getElementById('split_label_qty').value;
        if(label_qty==null || label_qty==''){
            mui.toast('拆分数量不能为空');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }

        if(!isAboveZeroFloat(label_qty) || parseFloat(label_qty)<=0.0){
            mui.toast('拆分数量必须是一个正数');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        if(parseFloat(label_qty) > product_qty){
            mui.toast('拆分数量不能超过被拆分标签的产品数量');
            if(!self.classList.contains('aas-error')){
                self.classList.add('aas-error');
            }
            return ;
        }
        label_qty = parseFloat(label_qty);
        document.getElementById('product_balance_qty').innerHTML = product_qty-label_qty;
    });

    var split_done_flag = false;
    document.getElementById('action_split').addEventListener('tap', function(){
        if(split_done_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        mui.confirm('您确认按照当前数量拆分标签？', '拆分标签', ['是', '否'], function(e) {
            if (e.index == 0) {
                action_splitlabel();
            } else {
                split_done_flag = false;
                return ;
            }
        });
    });


    function action_splitlabel(){
        if(split_done_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        split_done_flag = true;
        var split_label_qty = document.getElementById('split_label_qty');
        if(split_label_qty.value==null || split_label_qty.value==''){
            if(!split_label_qty.classList.contains('aas-error')){
                split_label_qty.classList.add('aas-error');
            }
        }
        var error_list = document.querySelectorAll('.aas-error');
        if(error_list!=undefined && error_list.length>0){
            mui.toast('您还有未处理的无效设置！');
            split_done_flag = false;
            return ;
        }
        var label_qty = parseFloat(split_label_qty.value);
        var label_id = parseInt(document.getElementById('label_split_pullrefresh').getAttribute('labelid'));
        var split_params = {'labelid': label_id, 'label_qty': label_qty};
        var split_access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var split_mask = aas_label_split_loading();
        mui.ajax('/aaswechat/mes/labelsplitdone', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: split_params, id: split_access_id }),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                split_done_flag = false;
                split_mask.close();
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/mes/labelsplitlist/'+label_id);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                split_done_flag = false;
                split_mask.close();
            }
        });
    }


});
