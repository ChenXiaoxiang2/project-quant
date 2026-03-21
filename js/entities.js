// entities.js - 实体数据与逻辑管理
// 定义玩家、敌机、子弹、粒子特效、道具等行为和状态

var Entities = {
    player: null,
    playerBullets: [],
    enemyBullets: [],
    enemies: [],
    particles: [],
    stars: [],
    powerUps: [],
    
    // 配置常量
    WEAPON_TYPES: ["基础激光", "双轨激光", "三向散射", "电浆重炮", "超维散射"],
    
    init: function() {
        this.playerBullets = [];
        this.enemyBullets = [];
        this.enemies = [];
        this.particles = [];
        this.powerUps = [];
        this.initStars();
        
        // 初始化玩家机体
        this.player = {
            x: Engine.width / 2 - 25,
            y: Engine.height - 100,
            width: 50,
            height: 60,
            speed: 300, // 像素/秒
            hp: 100,
            maxHp: 100,
            weaponLevel: 0,
            shootTimer: 0,
            shootInterval: 0.15, // 发射间隔(秒)
            invincibleTimer: 2 // 初始无敌时间 2 秒
        };
    },
    
    initStars: function() {
        this.stars = [];
        for (var i = 0; i < 150; i++) {
            this.stars.push({
                x: Math.random() * Engine.width,
                y: Math.random() * Engine.height,
                size: Math.random() * 2,
                speed: Math.random() * 100 + 50,
                brightness: Math.random()
            });
        }
    },
    
    // 创建粒子特效 (爆炸碎片)
    createExplosion: function(x, y, color, count) {
        for (var i = 0; i < count; i++) {
            var angle = Math.random() * Math.PI * 2;
            var speed = Math.random() * 150 + 50;
            this.particles.push({
                x: x,
                y: y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: 1.0,  // 生命周期 1秒
                maxLife: 1.0,
                color: color,
                size: Math.random() * 3 + 1
            });
        }
    },
    
    // 玩家射击逻辑（基于 weaponLevel）
    playerShoot: function() {
        var p = this.player;
        p.shootTimer += Engine.deltaTime;
        
        if (p.shootTimer >= p.shootInterval) {
            p.shootTimer = 0;
            var centerX = p.x + p.width / 2;
            var bY = p.y;
            
            // 武器等级逻辑
            var level = p.weaponLevel;
            var speed = 600; // 子弹速度 像素/秒
            
            if (level === 0) {
                // 单发基础
                this.playerBullets.push({ x: centerX - 2, y: bY, width: 4, height: 16, vx: 0, vy: -speed, type: 'laser' });
            } else if (level === 1) {
                // 双轨
                this.playerBullets.push({ x: centerX - 12, y: bY, width: 4, height: 16, vx: 0, vy: -speed, type: 'laser' });
                this.playerBullets.push({ x: centerX + 8, y: bY, width: 4, height: 16, vx: 0, vy: -speed, type: 'laser' });
            } else if (level === 2) {
                // 三向
                this.playerBullets.push({ x: centerX - 2, y: bY, width: 4, height: 16, vx: 0, vy: -speed, type: 'laser' });
                this.playerBullets.push({ x: centerX - 12, y: bY + 10, width: 4, height: 16, vx: -100, vy: -speed * 0.9, type: 'laser' });
                this.playerBullets.push({ x: centerX + 8, y: bY + 10, width: 4, height: 16, vx: 100, vy: -speed * 0.9, type: 'laser' });
            } else if (level === 3) {
                // 电浆重炮 (宽体子弹)
                this.playerBullets.push({ x: centerX - 10, y: bY, width: 20, height: 20, vx: 0, vy: -speed * 0.7, type: 'plasma', dmg: 3 });
            } else {
                // 5向终极散射
                this.playerBullets.push({ x: centerX - 2, y: bY, width: 4, height: 16, vx: 0, vy: -speed, type: 'laser' });
                this.playerBullets.push({ x: centerX - 15, y: bY + 5, width: 4, height: 16, vx: -80, vy: -speed * 0.95, type: 'laser' });
                this.playerBullets.push({ x: centerX + 11, y: bY + 5, width: 4, height: 16, vx: 80, vy: -speed * 0.95, type: 'laser' });
                this.playerBullets.push({ x: centerX - 25, y: bY + 15, width: 4, height: 16, vx: -160, vy: -speed * 0.85, type: 'laser' });
                this.playerBullets.push({ x: centerX + 21, y: bY + 15, width: 4, height: 16, vx: 160, vy: -speed * 0.85, type: 'laser' });
            }
        }
    },
    
    // 生成敌机
    spawnEnemy: function(difficultyScore) {
        var x = MathUtils.randomRange(0, Engine.width - 50);
        
        // 根据分数决定生成概率
        var r = Math.random();
        var enemyType, hp, width, height, speed, color;
        
        if (r < 0.15 && difficultyScore > 500) {
            // 巡洋舰 Cruiser
            enemyType = "cruiser";
            width = 80; height = 80;
            hp = 15; speed = 80; color = "#ff3333";
        } else if (r < 0.4 && difficultyScore > 200) {
            // 战机 Fighter
            enemyType = "fighter";
            width = 50; height = 50;
            hp = 5; speed = 150; color = "#ffaa00";
        } else {
            // 侦察机 Scout
            enemyType = "scout";
            width = 40; height = 40;
            hp = 2; speed = 250; color = "#ff00ff";
        }
        
        this.enemies.push({
            x: x, y: -height, 
            width: width, height: height, 
            hp: hp, maxHp: hp, speed: speed, 
            type: enemyType, color: color,
            shootTimer: 0
        });
    },
    
    // 敌机行为控制
    enemyLogic: function(enemy) {
        var dt = Engine.deltaTime;
        enemy.y += enemy.speed * dt;
        enemy.shootTimer += dt;
        
        var centerX = enemy.x + enemy.width/2;
        var bottomY = enemy.y + enemy.height;
        var bSpeed = 300;
        
        if (enemy.type === "fighter" && enemy.shootTimer > 1.5) {
            enemy.shootTimer = 0;
            this.enemyBullets.push({ x: centerX - 3, y: bottomY, width: 6, height: 15, vx: 0, vy: bSpeed, color: "#ffaa00" });
        } else if (enemy.type === "cruiser" && enemy.shootTimer > 2.0) {
            enemy.shootTimer = 0;
            // 散弹
            this.enemyBullets.push({ x: centerX - 4, y: bottomY, width: 8, height: 18, vx: 0, vy: bSpeed, color: "#ff3333" });
            this.enemyBullets.push({ x: centerX - 4, y: bottomY, width: 8, height: 18, vx: -100, vy: bSpeed * 0.9, color: "#ff3333" });
            this.enemyBullets.push({ x: centerX - 4, y: bottomY, width: 8, height: 18, vx: 100, vy: bSpeed * 0.9, color: "#ff3333" });
        }
    },
    
    // 掉落道具
    dropPowerUp: function(x, y) {
        if (Math.random() < 0.15) { // 15% 概率掉落武器升级
            this.powerUps.push({
                x: x, y: y,
                width: 20, height: 20,
                type: "weapon",
                vy: 100,
                color: "#00ffcc"
            });
        } else if (Math.random() < 0.05) { // 5% 概率掉落回血
            this.powerUps.push({
                x: x, y: y,
                width: 20, height: 20,
                type: "health",
                vy: 120,
                color: "#00ff00"
            });
        }
    }
};