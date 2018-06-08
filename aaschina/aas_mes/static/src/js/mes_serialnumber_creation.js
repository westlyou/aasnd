/**
 * Created by luforn on 2017-10-12.
 */

$(function() {

    var serialprinterstr = localStorage.getItem('serialprinter');
    if(serialprinterstr!=null && serialprinterstr!=''){
        var serialprinter = JSON.parse(serialprinterstr);
        $('#printerlist').val(serialprinter.printer_id);
        $('#printerlist').html("<option value="+serialprinter.printer_id+">"+serialprinter.printer_name+"</option>");
    }



    function isAboveZeroFloat(val){
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)){ return true; }
        return false;
    }

    $('#action_addserial').click(function(){
        var printerid = $('#printerlist').val();
        if(printerid==null || printerid=='0'){
            layer.msg('请先设置好标签打印机！', {icon: 5});
            return ;
        }
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/serialnumber/checkingmesline',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {}, id: access_id}),
            success:function(data){
                var dresult = data.result;
                $('#serial_supplier').innerHTML = dresult.serial_supplier;
                $('#serial_mesline').innerHTML = dresult.mesline_name;
                $('#serial_year').innerHTML = dresult.serial_year;
                $('#serial_week').innerHTML = dresult.serial_week;
                $('#serial_weekday').innerHTML = dresult.serial_weekday;
                $('#serial_type').innerHTML = dresult.serial_type;
                $('#serial_extend').innerHTML = dresult.serial_extend;
                $('#customer_code').innerHTML = dresult.customer_code;
                $('#product_code').innerHTML = dresult.product_code;
                $('#serial_message').innerHTML = dresult.message;
                $('#serial_count').html(dresult.serial_count);
                $('#lastserialnumber').html(dresult.lastserialnumber);
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                layer.prompt({title: '输入序列号数量，并确认', formType: 3}, function(text, index){
                    if(!isAboveZeroFloat(text)){
                        layer.msg('序列号的数量必须是一个大于零的整数！', {icon: 5});
                        return ;
                    }
                    var serialcount = parseInt(text);
                    if(serialcount > 200){
                        layer.msg('一次最多生成200个序列号！', {icon: 5});
                        return ;
                    }
                    layer.close(index);
                    var tempid = Math.floor(Math.random() * 1000 * 1000 * 1000);
                    $.ajax({
                        url: '/aasmes/serialnumber/adddone',
                        headers: {'Content-Type': 'application/json'},
                        type: 'post', timeout: 10000, dataType: 'json',
                        data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'serialcount': serialcount}, id: tempid}),
                        success: function (data) {
                            $('#serialnumberlist').html('');
                            var dresult = data.result;
                            if(!dresult.success){
                                layer.msg(dresult.message, {icon: 5});
                                return ;
                            }
                            $('#serial_count').html(dresult.serial_count);
                            $('#lastserialnumber').html(dresult.lastserialnumber);
                            loadingserialnumberlist(1, 200);
                            //自动打印标签
                            autoprinting();
                        },
                        error: function (xhr, type, errorThrown) {
                            console.log(type);
                        }
                    });
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });

    $('#printerlist').select2({
        placeholder: '选择标签打印机',
        ajax:{
            type: 'post',
            timeout:10000,
            dataType: 'json',
            url: '/aasmes/printerlist',
            headers:{'Content-Type':'application/json'},
            data: function(params){
                var sparams =  {'q': params.term || '', 'page': params.page || 1};
                var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
                return JSON.stringify({ jsonrpc: "2.0", method: 'call', params: sparams, id: accessid})
            },
            processResults: function (data, params) {
                params.page = params.page || 1;
                var dresult = data.result;
                return {
                    results: dresult.items,
                    pagination: {more: (params.page * 30) < dresult.total_count}
                };
            }
        }
    });

    $('#printerlist').on('select2:select', function(event){
        var selectedatas = $('#printerlist').select2('data');
        var printerobj = selectedatas[0];
        var printer = {'printer_id': printerobj.id, 'printer_name': printerobj.text};
        localStorage.setItem('serialprinter', JSON.stringify(printer));
    });

    //打印标签
    $('#action_printing').click(function(){
        var printerid = $('#printerlist').val();
        if(printerid==null || printerid=='0'){
            layer.msg('请先设置好标签打印机！', {icon: 5});
            return ;
        }
        var serialnumberlist = $('input.aas-active');
        if(serialnumberlist==undefined || serialnumberlist==null || serialnumberlist.length<=0){
            layer.msg('请先选择需要打印的标签！', {icon: 5});
            return ;
        }
        var printerid = parseInt(printerid);
        var serialids = [];
        $.each(serialnumberlist, function(index, serialipt){
            serialids.push(parseInt($(serialipt).attr('serialid')));
        });
        var params = {'printerid': printerid, 'serialids': serialids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/serialnumber/loadingserialnumbers',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 10000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: params, id: access_id}),
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var printername = dresult.printer;
                var printcount = 1 ;
                var printerurl = dresult.serverurl;
                $.each(dresult.records, function(index, record){
                    var params = {'label_name': printername, 'label_count': printcount, 'label_content':record};
                    $.ajax({type:'post', dataType:'script', url:'http://'+printerurl, data: params,
                        success: function (result) { },
                        error:function(XMLHttpRequest,textStatus,errorThrown){}
                    });
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });

    //条码重打
    $('#action_reprint').click(function(){
        var printerid = $('#printerlist').val();
        if(printerid==null || printerid=='0'){
            layer.msg('请先设置好标签打印机！', {icon: 5});
            return ;
        }
        layer.prompt({title: '输入或扫描二维码', formType: 3}, function(text, index){
            if(text==undefined || text==null || text==''){
                layer.msg('请输入一个有效的条码！', {icon: 5});
                return ;
            }
            layer.close(index);
            var tparams = {'printerid': printerid, 'serialnumber': text};
            var tempid = Math.floor(Math.random() * 1000 * 1000 * 1000);
            $.ajax({
                url: '/aasmes/serialnumber/reprint',
                headers: {'Content-Type': 'application/json'},
                type: 'post', timeout: 10000, dataType: 'json',
                data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: tparams, id: tempid}),
                success: function (data) {
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    var printername = dresult.printer;
                    var printerurl = dresult.serverurl;
                    var temprecords = dresult.records;
                    if(temprecords.length <= 0){
                        layer.msg('未获取到需要打印的条码', {icon: 5});
                        return ;
                    }
                    var record = temprecords[0];
                    var pparams = {'label_name': printername, 'label_count': 1, 'label_content':record};
                    $.ajax({type:'post', dataType:'script', url:'http://'+printerurl, data: pparams,
                        success: function (result) { },
                        error:function(XMLHttpRequest,textStatus,errorThrown){}
                    });
                },
                error: function (xhr, type, errorThrown) {
                    console.log(type);
                }
            });
        });
    });

    $("#checkall").click(function () {
        var clicked = $(this).data('clicked');
        if (clicked) {
            $(".mailbox-messages input[type='checkbox']").iCheck("uncheck");
            $(".fa", this).removeClass("fa-check-square-o").addClass('fa-square-o');
          } else {
            $(".mailbox-messages input[type='checkbox']").iCheck("check");
            $(".fa", this).removeClass("fa-square-o").addClass('fa-check-square-o');
          }
          $(this).data("clicked", !clicked);
    });

    //加载序列号清单
    function loadingserialnumberlist(page, limit){
        var tparams = {'page': page, 'limit': limit};
        var tempid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/serialnumber/loadingmore',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 10000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: tparams, id: tempid}),
            success: function (data) {
                $('#serialnumberlist').html('');
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var firstno = ((page-1) * limit) + 1;
                var lastno = page * limit;
                if (dresult.count < limit){
                    lastno = firstno - 1 + dresult.count;
                }
                var serialcount_content = firstno+'-'+lastno+'/'+dresult.total;
                $('#serialcount_content').html(serialcount_content);
                $('#action_prepage').attr({'page': page, 'limit': limit, 'total': dresult.total});
                $('#action_nxtpage').attr({'page': page, 'limit': limit, 'total': dresult.total});
                if (dresult.recordlist.length <= 0){
                    return ;
                }
                $.each(dresult.recordlist, function(index, record){
                    var serialitem = $("<tr class='aas-serialnumber'></tr>");
                    var serialcontent = "<td><input type='checkbox' serialid="+record.serialnumber_id+"></td>";
                    serialcontent += "<td>"+record.serialnumber_name+"</td>";
                    serialcontent += "<td>"+record.sequence_code+"</td>";
                    serialcontent += "<td>"+record.product_code+"</td>";
                    serialcontent += "<td>"+record.customer_code+"</td>";
                    serialitem.html(serialcontent);
                    $('#serialnumberlist').append(serialitem);
                });
                $('.mailbox-messages input[type="checkbox"]').iCheck({checkboxClass: 'icheckbox_flat-blue'});
                $(".mailbox-messages input[type='checkbox']").on('ifChecked', function(event){
                    $(this).addClass('aas-active');
                });
                $(".mailbox-messages input[type='checkbox']").on('ifUnchecked', function(event){
                    $(this).removeClass('aas-active');
                    if($('.fa', '#checkall').hasClass('fa-check-square-o')){
                        $('.fa', '#checkall').removeClass("fa-check-square-o").addClass('fa-square-o');
                    }
                });
            },
            error: function (xhr, type, errorThrown) {
                console.log(type);
            }
        });

    }

    $('#action_prepage').click(function(){
        var page = parseInt($(this).attr('page'));
        var limit = parseInt($(this).attr('limit'));
        var total = parseInt($(this).attr('total'));
        if(page <= 1){
            layer.msg('当前已经是第一页了！', {icon: 5});
            return ;
        }
        page -= 1;
        loadingserialnumberlist(page, limit);
    });

    $('#action_nxtpage').click(function(){
        var page = parseInt($(this).attr('page'));
        var limit = parseInt($(this).attr('limit'));
        var total = parseInt($(this).attr('total'));
        if(page*limit >= total){
            layer.msg('当前已经是第后一页了！', {icon: 5});
            return ;
        }
        page += 1;
        loadingserialnumberlist(page, limit);
    });

    loadingserialnumberlist(1, 200);


    // 自动打印标签
    function autoprinting(){
        var printerid = $('#printerlist').val();
        if(printerid==null || printerid=='0'){
            layer.msg('请先设置好标签打印机！', {icon: 5});
            return ;
        }
        var tparams = {'printerid': parseInt(printerid)};
        var tempid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/serialnumber/autoprint',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 10000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: tparams, id: tempid}),
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var printername = dresult.printer;
                var printerurl = dresult.serverurl;
                var temprecords = dresult.records;
                if(temprecords.length <= 0){
                    layer.msg('未获取到需要打印的条码', {icon: 5});
                    return ;
                }
                $.each(temprecords, function(index, record){
                    var pparams = {'label_name': printername, 'label_count': 1, 'label_content':record};
                    $.ajax({type:'post', dataType:'script', url:'http://'+printerurl, data: pparams,
                        success: function (result) { },
                        error:function(XMLHttpRequest,textStatus,errorThrown){}
                    });
                });
            },
            error: function (xhr, type, errorThrown) {
                console.log(type);
            }
        });
    }

});