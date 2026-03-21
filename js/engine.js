// engine.js - 核心引擎模块
// 负责画布管理、输入捕获、基础数学和碰撞检测

var Engine = {
    canvas: null,
    ctx: null,
    width: 0,
    height: 0,
    lastTime: 0,
    deltaTime: 0,
    state: "MENU", // "MENU", "PLAYING", "PAUSED", "GAMEOVER"
    score: 0,
    level: 1,
    
    init: function() {
        this.canvas = document.getElementById("gameCanvas");
        this.ctx = this.canvas.getContext("2d");
        
        // 绑定窗口调整事件
        window.addEventListener("resize", this.resize.bind(this));
        this.resize();
        
        Input.init(this.canvas);
        Assets.init(); // 提前生成静态资源
    },
    
    resize: function() {
        this.width = window.innerWidth > 640 ? 640 : window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
    },
    
    updateTime: function(timestamp) {
        if (!this.lastTime) this.lastTime = timestamp;
        this.deltaTime = (timestamp - this.lastTime) / 1000; // 转换为秒
        // 防止切后台后回来 deltaTime 过大导致穿墙或逻辑爆炸
        if (this.deltaTime > 0.1) this.deltaTime = 0.1; 
        this.lastTime = timestamp;
    }
};

var Input = {
    keys: {},
    isTouching: false,
    touchX: 0,
    touchY: 0,
    action: false, // 用于表示“重新开始”之类的操作
    
    init: function(canvas) {
        var self = this;
        
        window.addEventListener("keydown", function(e) {
            self.keys[e.key] = true;
            if(e.key === " ") self.action = true;
        });
        
        window.addEventListener("keyup", function(e) {
            self.keys[e.key] = false;
        });
        
        canvas.addEventListener("touchstart", function(e) {
            e.preventDefault();
            self.isTouching = true;
            self.touchX = e.touches[0].clientX - canvas.offsetLeft;
            self.touchY = e.touches[0].clientY;
            self.action = true; // 触摸时触发动作
        }, {passive: false});
        
        canvas.addEventListener("touchmove", function(e) {
            e.preventDefault();
            if (self.isTouching) {
                self.touchX = e.touches[0].clientX - canvas.offsetLeft;
                self.touchY = e.touches[0].clientY;
            }
        }, {passive: false});
        
        canvas.addEventListener("touchend", function(e) {
            e.preventDefault();
            self.isTouching = false;
        }, {passive: false});
        
        // 兼容鼠标拖拽
        var isMouseDown = false;
        canvas.addEventListener("mousedown", function(e) {
            isMouseDown = true;
            self.isTouching = true;
            self.touchX = e.clientX - canvas.offsetLeft;
            self.action = true;
        });
        canvas.addEventListener("mousemove", function(e) {
            if (isMouseDown) {
                self.touchX = e.clientX - canvas.offsetLeft;
            }
        });
        window.addEventListener("mouseup", function(e) {
            isMouseDown = false;
            self.isTouching = false;
        });
    },
    
    consumeAction: function() {
        if (this.action) {
            this.action = false;
            return true;
        }
        return false;
    }
};

var MathUtils = {
    randomRange: function(min, max) {
        return Math.random() * (max - min) + min;
    },
    
    // AABB 预检 + 圆形精确碰撞
    checkCollision: function(obj1, obj2, hitboxScale) {
        hitboxScale = hitboxScale || 0.6; // 核心判定区比例
        
        // Broad Phase
        if (obj1.x > obj2.x + obj2.width || 
            obj1.x + obj1.width < obj2.x || 
            obj1.y > obj2.y + obj2.height || 
            obj1.y + obj1.height < obj2.y) {
            return false;
        }
        
        // Narrow Phase (Circle vs Circle)
        var r1 = (Math.min(obj1.width, obj1.height) / 2) * hitboxScale;
        var r2 = (Math.min(obj2.width, obj2.height) / 2) * hitboxScale;
        
        var cx1 = obj1.x + obj1.width / 2;
        var cy1 = obj1.y + obj1.height / 2;
        var cx2 = obj2.x + obj2.width / 2;
        var cy2 = obj2.y + obj2.height / 2;
        
        var dx = cx1 - cx2;
        var dy = cy1 - cy2;
        return (dx * dx + dy * dy) < ((r1 + r2) * (r1 + r2));
    }
};