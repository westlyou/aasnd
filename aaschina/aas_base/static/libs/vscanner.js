var VScanner = function(callback){
    /**
     * keydown与keyup的event.which值均为触发事件的键的代码
     * keypress的event.which值为事件触发的键的值的字符代码即相应字符的ascii码
    */

    this.barcode = '';
    this.delaytimes = 50; //keydown和keyup之间的延迟毫秒
    this.scanning = true; // 是否扫描模式
    this.charlist = [];
    this.timelist = [];
    this.callback = callback;
    var self = this;

    _keycode_dictionary = {
        48: "0", 49: "1", 50: "2", 51: "3", 52: "4", 53: "5", 54: "6" , 55: "7", 56: "8", 57: "9",
        96: "0", 97: "1", 98: "2", 99: "3", 100: "4", 101: "5", 102: "6", 103: "7", 104: "8", 105: "9",
        65: "a", 66: "b", 67: "c", 68: "d", 69: "e", 70: "f", 71: "g", 72: "h", 73: "i", 74: "j", 75: "k", 76: "l", 77: "m",
        78: "n", 79: "o", 80: "p", 81: "q", 82: "r", 83: "s", 84: "t", 85: "u", 86: "v", 87: "w", 88: "x", 89: "y", 90: "z",
        0: "\\", 220: "\\", 61: "=", 187: "=", 173: "-", 189: "-", 192: "`", 223: "`",
        188: ",", 190: ".", 191: "/", 219: "[", 221: "]", 222: "\'", 59: ";"
    };

    _keycode_shifted_dictionary = {
        48: ")", 49: "!", 50: "@", 51: "#", 52: "$", 53: "%", 54: "^" , 55: "&", 56: "*", 57: "(",
        65: "A", 66: "B", 67: "C", 68: "D", 69: "E", 70: "F", 71: "G", 72: "H", 73: "I", 74: "J", 75: "K", 76: "L", 77: "M",
        78: "N", 79: "O", 80: "P", 81: "Q", 82: "R", 83: "S", 84: "T", 85: "U", 86: "V", 87: "W", 88: "X", 89: "Y", 90: "Z",
        61: "+", 187: "+", 173: "_", 189: "_", 192: "~", 223: "~",
        188: "<", 190: ">", 191: "?", 219: "{", 221: "}", 222: "|'", 59: ":"
    };


    document.body.addEventListener('keydown', function(event){
        if (!self.scanning){
            return ;
        }
        var keycode = event.which;
        if (keycode in _keycode_dictionary){
            self.timelist.push(new Date().getTime());
        }else if(keycode==13 || keycode==108){
            self.timelist.push(new Date().getTime());
        }
    });
    document.body.addEventListener('keypress', function(event){
        if (!self.scanning || event.which==13){
            return ;
        }
        self.charlist.push(String.fromCharCode(event.which));
    });
    document.body.addEventListener('keyup', function(event){
        if (!self.scanning){
            return ;
        }
        var keycode = event.which;
        if (keycode in _keycode_dictionary){
            var starttime = self.timelist.shift();
            var finishtime = new Date().getTime();
            if (finishtime - starttime <= self.delaytimes){
                self.barcode += self.charlist.shift();
            }
        }else if (keycode==13 || keycode==108){
            var starttime = self.timelist.shift();
            var finishtime = new Date().getTime();
            if (finishtime - starttime <= self.delaytimes){
                self.actionscan(self.barcode);
                self.clear();
            }
		}
    });


};


VScanner.prototype.actionscan = function(barcode){
	this.callback(barcode);
};

VScanner.prototype.clear = function(){
    this.barcode = '';
    this.charlist = [];
    this.timelist = [];
}