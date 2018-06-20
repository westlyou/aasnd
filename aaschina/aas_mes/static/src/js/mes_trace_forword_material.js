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
        var mid = $(self).attr('mid');
        var mids = mid.split('-');
        var temparams = {'productid': parseInt(mids[1]), 'protlotid': parseInt(mids[2])};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $(self).attr('doing', '1');
        $.ajax({
            url: '/aasmes/product/forward/loadingmaterialist',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 30000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            success: function (data) {
                $(self).attr('doing', '0');
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var materiallist = dresult.materiallist;
                if(materiallist==undefined || materiallist==null || materiallist.length<=0){
                    layer.msg('未追溯到原料信息！', {icon: 5});
                    return ;
                }
                $('.aas-takeup', $('#'+parentid)).show();
                $(self).hide();
                var templist = parentid.split('-');
                var level = templist.length;
                var levelstr = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'.repeat(level-1);
                $.each(materiallist, function(index, material){
                    var materialtr = $('<tr></tr>').attr('id', parentid+'-'+index).insertAfter($('#'+parentid));
                    $('<td></td>').html(levelstr+material['material_code']).appendTo(materialtr);
                    $('<td></td>').html(material['matllot_code']).appendTo(materialtr);
                    $('<td></td>').html(material['mesline_name']).appendTo(materialtr);
                    $('<td></td>').html(level).appendTo(materialtr);
                    var operatetd = $('<td style="cursor: pointer;"></td>').appendTo(materialtr);
                    $('<span class="label label-success aas-tracing" doing="0">追溯</span>').attr('mid', material['mid']).appendTo(operatetd).click(function(){
                        action_tracing(this);
                    });
                    $('<span class="label label-info aas-takeup" style="display:none">收起</span>').attr('mid', material['mid']).appendTo(operatetd).click(function(){
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
