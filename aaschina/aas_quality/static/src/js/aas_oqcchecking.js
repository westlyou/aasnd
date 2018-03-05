/**
 * Created by luforn on 2018-3-5.
 */

$(function(){

    new VScanner(function(barcode){
        if(barcode==null || barcode==''){
            layer.msg('扫描条码异常！', {icon: 5});
            return ;
        }
        action_scan_label(barcode);
    });

    //扫描标签
    function action_scan_label(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasquality/oqcchecking/scanlabel',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var pid = $('#quality_product').attr('pid');
                if(pid==0 || pid== '0'){
                    $('#quality_product').attr({'pid': dresult.product_id})
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }


});
