/**
 * Created by luforn on 2018-6-19.
 */

$(function(){

    String.prototype.repeat = String.prototype.repeat || function(num) {
        return new Array(num + 1).join(this);
    };

    //逐级追溯
    $('.aas-tracing').click(function(){
        action_tracing(this);
    });

    //收起追溯信息
    $('.aas-takeup').click(function(){
        action_takeup(this);
    });

    function action_tracing(traceitem){
        var self = traceitem;
        var doing = parseInt($(self).attr('doing'));
        if(doing==1){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        var parentid = $(self).parent().parent().attr('id');
        var pid = $(self).attr('pid');
        var pids = pid.split('-');
        var temparams = {'materialid': parseInt(pids[1]), 'matllotid': parseInt(pids[2])};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $(self).attr('doing', '1');
        $.ajax({
            url: '/aasmes/material/reverse/loadingproductlist',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 60000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            success: function (data) {
                $(self).attr('doing', '0');
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var productlist = dresult.productlist;
                if(productlist==undefined || productlist==null || productlist.length<=0){
                    layer.msg('未追溯到成品信息！', {icon: 5});
                    return ;
                }
                $('.aas-takeup', $('#'+parentid)).show();
                $(self).hide();
                var templist = parentid.split('-');
                var level = templist.length;
                var levelstr = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'.repeat(level-1);
                $.each(productlist, function(index, product){
                    var producttr = $('<tr></tr>').attr('id', parentid+'-'+index).insertAfter($('#'+parentid));
                    $('<td></td>').html(levelstr+product['product_code']).appendTo(producttr);
                    $('<td></td>').html(product['protlot_code']).appendTo(producttr);
                    $('<td></td>').html(product['mesline_name']).appendTo(producttr);
                    $('<td></td>').html(level).appendTo(producttr);
                    var operatetd = $('<td style="cursor: pointer;"></td>').appendTo(producttr);
                    $('<span class="label label-success aas-tracing" doing="0">追溯</span>').attr('pid', product['pid']).appendTo(operatetd).click(function(){
                        action_tracing(this);
                    });
                    $('<span class="label label-info aas-takeup" style="display:none">收起</span>').attr('pid', product['pid']).appendTo(operatetd).click(function(){
                        action_takeup(this);
                    });
                });
            },
            error: function (xhr, type, errorThrown) {
                console.log(type);
                $(self).attr('doing', '0');
            }
        });
    }

    function action_takeup(traceitem){
        var self = traceitem;
        var parentid = $(self).parent().parent().attr('id');
        var childlist = $("tr[id^="+parentid+"-]");
        if(childlist!=undefined && childlist!=null && childlist.length>0){
            childlist.remove();
        }
        $('.aas-tracing', $('#'+parentid)).show();
        $(self).hide();
    }




});
