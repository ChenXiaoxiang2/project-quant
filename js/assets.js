// assets.js - 资源管理器与动态离线 Canvas 精灵图生成

var Assets = {
    images: {},
    
    init: function() {
        this.images.player = this.createPlayerSprite();
        this.images.scout = this.createEnemySprite("scout");
        this.images.fighter = this.createEnemySprite("fighter");
        this.images.cruiser = this.createEnemySprite("cruiser");
        this.images.boss1 = this.createBossSprite(1);
        this.images.boss2 = this.createBossSprite(2);
        this.images.boss3 = this.createBossSprite(3);
    },
    
    get: function(name) {
        return this.images[name];
    },
    
    _createCanvas: function(w, h) {
        var c = document.createElement("canvas");
        c.width = w;
        c.height = h;
        return { c: c, ctx: c.getContext("2d") };
    },
    
    createPlayerSprite: function() {
        var obj = this._createCanvas(100, 100);
        var ctx = obj.ctx;
        // 阴影发光
        ctx.shadowBlur = 15;
        ctx.shadowColor = "#00aaff";
        
        // 主机翼
        ctx.fillStyle = "#0055ff";
        ctx.beginPath();
        ctx.moveTo(50, 10);
        ctx.lineTo(95, 90);
        ctx.lineTo(50, 70);
        ctx.lineTo(5, 90);
        ctx.closePath();
        ctx.fill();
        
        // 机身装甲
        ctx.fillStyle = "#00ffff";
        ctx.beginPath();
        ctx.moveTo(50, 15);
        ctx.lineTo(70, 75);
        ctx.lineTo(50, 60);
        ctx.lineTo(30, 75);
        ctx.closePath();
        ctx.fill();
        
        // 核心能量舱
        ctx.fillStyle = "#ffffff";
        ctx.shadowColor = "#ffffff";
        ctx.beginPath();
        ctx.arc(50, 55, 8, 0, Math.PI * 2);
        ctx.fill();
        
        return obj.c;
    },
    
    createEnemySprite: function(type) {
        var obj = this._createCanvas(100, 100);
        var ctx = obj.ctx;
        
        if (type === "scout") { // 紫色快速侦查机 (倒三角)
            ctx.shadowBlur = 10;
            ctx.shadowColor = "#ff00ff";
            ctx.fillStyle = "#aa00aa";
            ctx.beginPath();
            ctx.moveTo(50, 90);
            ctx.lineTo(80, 10);
            ctx.lineTo(50, 30);
            ctx.lineTo(20, 10);
            ctx.closePath();
            ctx.fill();
            
            ctx.fillStyle = "#ff88ff";
            ctx.beginPath();
            ctx.moveTo(50, 80);
            ctx.lineTo(65, 25);
            ctx.lineTo(50, 40);
            ctx.lineTo(35, 25);
            ctx.closePath();
            ctx.fill();
        } 
        else if (type === "fighter") { // 橙色中型战机
            ctx.shadowBlur = 15;
            ctx.shadowColor = "#ffaa00";
            ctx.fillStyle = "#dd6600";
            ctx.beginPath();
            ctx.moveTo(50, 80);
            ctx.lineTo(90, 30);
            ctx.lineTo(70, 10);
            ctx.lineTo(50, 40);
            ctx.lineTo(30, 10);
            ctx.lineTo(10, 30);
            ctx.closePath();
            ctx.fill();
            
            ctx.fillStyle = "#ffcc44";
            ctx.fillRect(40, 50, 20, 30);
        }
        else if (type === "cruiser") { // 红色重型巡洋舰
            ctx.shadowBlur = 20;
            ctx.shadowColor = "#ff0000";
            ctx.fillStyle = "#880000";
            ctx.beginPath();
            ctx.moveTo(30, 10);
            ctx.lineTo(70, 10);
            ctx.lineTo(90, 50);
            ctx.lineTo(70, 90);
            ctx.lineTo(30, 90);
            ctx.lineTo(10, 50);
            ctx.closePath();
            ctx.fill();
            
            ctx.fillStyle = "#ff3333";
            ctx.fillRect(35, 35, 30, 30);
            ctx.fillStyle = "#ffff00";
            ctx.beginPath();
            ctx.arc(50, 50, 10, 0, Math.PI * 2);
            ctx.fill();
        }
        return obj.c;
    },
    
    createBossSprite: function(level) {
        var obj = this._createCanvas(200, 200);
        var ctx = obj.ctx;
        
        if (level === 1) { // 机械巨蟹
            ctx.shadowBlur = 20;
            ctx.shadowColor = "#ff4444";
            
            ctx.fillStyle = "#550000";
            ctx.beginPath();
            ctx.moveTo(100, 180);
            ctx.lineTo(180, 120);
            ctx.lineTo(180, 40);
            ctx.lineTo(100, 10);
            ctx.lineTo(20, 40);
            ctx.lineTo(20, 120);
            ctx.closePath();
            ctx.fill();
            
            ctx.fillStyle = "#aa1111";
            ctx.beginPath();
            ctx.moveTo(100, 150);
            ctx.lineTo(150, 100);
            ctx.lineTo(150, 50);
            ctx.lineTo(100, 30);
            ctx.lineTo(50, 50);
            ctx.lineTo(50, 100);
            ctx.closePath();
            ctx.fill();
            
            // 引擎/眼睛
            ctx.fillStyle = "#ffff00";
            ctx.shadowColor = "#ffff00";
            ctx.beginPath();
            ctx.arc(60, 80, 15, 0, Math.PI * 2);
            ctx.arc(140, 80, 15, 0, Math.PI * 2);
            ctx.fill();
        }
        else if (level === 2) { // 幽灵战机
            ctx.shadowBlur = 20;
            ctx.shadowColor = "#00ff00";
            
            ctx.fillStyle = "#112211";
            ctx.beginPath();
            ctx.moveTo(100, 180);
            ctx.lineTo(190, 60);
            ctx.lineTo(100, 20);
            ctx.lineTo(10, 60);
            ctx.closePath();
            ctx.fill();
            
            ctx.fillStyle = "#22aa22";
            ctx.beginPath();
            ctx.moveTo(100, 150);
            ctx.lineTo(160, 70);
            ctx.lineTo(100, 40);
            ctx.lineTo(40, 70);
            ctx.closePath();
            ctx.fill();
            
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.arc(100, 100, 15, 0, Math.PI * 2);
            ctx.fill();
        }
        else if (level === 3) { // 终极母舰
            ctx.shadowBlur = 30;
            ctx.shadowColor = "#aa00ff";
            
            ctx.fillStyle = "#110022";
            ctx.beginPath();
            ctx.arc(100, 100, 90, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.fillStyle = "#330066";
            ctx.beginPath();
            ctx.arc(100, 100, 70, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.fillStyle = "#8800cc";
            ctx.beginPath();
            ctx.arc(100, 100, 40, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.fillStyle = "#00ffff";
            ctx.shadowColor = "#00ffff";
            ctx.beginPath();
            ctx.arc(50, 100, 15, 0, Math.PI * 2);
            ctx.arc(150, 100, 15, 0, Math.PI * 2);
            ctx.fill();
        }
        return obj.c;
    }
};