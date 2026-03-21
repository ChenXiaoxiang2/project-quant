// main.js - 游戏主控逻辑
// 负责组装引擎、实体、渲染器，处理游戏状态流转与碰撞结算

var Main = {
    difficultyTimer: 0,
    spawnInterval: 1.5,
    spawnTimer: 0,
    bossActive: false,
    
    start: function() {
        Engine.init();
        requestAnimationFrame(this.loop.bind(this));
    },
    
    startNewGame: function() {
        document.getElementById("menu-start").style.display = "none";
        document.getElementById("menu-gameover").style.display = "none";
        document.getElementById("menu-pause").style.display = "none";
        document.getElementById("pauseBtn").style.display = "block";
        document.getElementById("bossHpContainer").style.display = "none";
        
        Engine.state = "PLAYING";
        Engine.score = 0;
        Engine.level = 1;
        this.difficultyTimer = 0;
        this.spawnInterval = 1.5;
        this.spawnTimer = 0;
        this.bossActive = false;
        
        Entities.init();
    },
    
    pauseGame: function() {
        if (Engine.state === "PLAYING") {
            Engine.state = "PAUSED";
            document.getElementById("menu-pause").style.display = "block";
            document.getElementById("pauseBtn").style.display = "none";
        }
    },
    
    resumeGame: function() {
        if (Engine.state === "PAUSED") {
            Engine.state = "PLAYING";
            document.getElementById("menu-pause").style.display = "none";
            document.getElementById("pauseBtn").style.display = "block";
            Engine.lastTime = 0; // 重置时间以防突跳
        }
    },
    
    endGame: function() {
        Engine.state = "GAMEOVER";
        document.getElementById("menu-gameover").style.display = "block";
        document.getElementById("pauseBtn").style.display = "none";
        document.getElementById("bossHpContainer").style.display = "none";
        document.getElementById("finalScore").innerText = "最终得分: " + Engine.score;
        
        var p = Entities.player;
        if(p) Entities.createExplosion(p.x + p.width/2, p.y + p.height/2, "#00ffff", 50);
        Entities.player = null;
    },
    
    loop: function(timestamp) {
        Engine.updateTime(timestamp);
        
        if (Engine.state === "PLAYING") {
            this.update();
        } else if (Engine.state === "GAMEOVER") {
            this.updateParticlesOnly();
        }
        
        Renderer.draw(Engine.ctx, Engine.width, Engine.height);
        requestAnimationFrame(this.loop.bind(this));
    },
    
    updateParticlesOnly: function() {
        var dt = Engine.deltaTime;
        for (var i = Entities.particles.length - 1; i >= 0; i--) {
            var p = Entities.particles[i];
            p.x += p.vx * dt;
            p.y += p.vy * dt;
            p.life -= dt;
            if (p.life <= 0) Entities.particles.splice(i, 1);
        }
    },
    
    update: function() {
        var dt = Engine.deltaTime;
        var p = Entities.player;
        
        // 1. 玩家移动
        if (Input.keys["ArrowLeft"] && p.x > 0) p.x -= p.speed * dt;
        if (Input.keys["ArrowRight"] && p.x < Engine.width - p.width) p.x += p.speed * dt;
        if (Input.keys["ArrowUp"] && p.y > 0) p.y -= p.speed * dt;
        if (Input.keys["ArrowDown"] && p.y < Engine.height - p.height) p.y += p.speed * dt;
        
        if (Input.isTouching) {
            var targetX = Input.touchX - p.width / 2;
            var targetY = Input.touchY - p.height / 2;
            if (targetX < 0) targetX = 0;
            if (targetX > Engine.width - p.width) targetX = Engine.width - p.width;
            if (targetY < 0) targetY = 0;
            if (targetY > Engine.height - p.height) targetY = Engine.height - p.height;
            p.x += (targetX - p.x) * 10 * dt;
            p.y += (targetY - p.y) * 10 * dt;
        }
        
        // 2. 关卡与 Boss 逻辑
        if (!this.bossActive) {
            this.difficultyTimer += dt;
            // 每关时长 30 秒，到达 30 秒召唤 Boss
            if (this.difficultyTimer > 30) {
                this.bossActive = true;
                Entities.spawnBoss(Engine.level);
            } else {
                this.spawnTimer += dt;
                if (this.spawnTimer >= this.spawnInterval) {
                    this.spawnTimer = 0;
                    Entities.spawnEnemy(Engine.score, Engine.level);
                }
            }
        } else {
            // Boss 战期间，检查 Boss 是否死亡
            var bossExists = false;
            for (var i = 0; i < Entities.enemies.length; i++) {
                if (Entities.enemies[i].isBoss) {
                    bossExists = true;
                    // 更新 Boss 血条
                    var hpBar = document.getElementById("bossHpBar");
                    hpBar.style.width = Math.max(0, (Entities.enemies[i].hp / Entities.enemies[i].maxHp) * 100) + "%";
                    break;
                }
            }
            if (!bossExists) {
                // Boss 死亡，进入下一关
                this.bossActive = false;
                Engine.level++;
                this.difficultyTimer = 0;
                this.spawnInterval = Math.max(0.4, 1.5 - (Engine.level * 0.2));
                document.getElementById("bossHpContainer").style.display = "none";
                Engine.score += 1000 * Engine.level;
                // 清屏
                Entities.enemies = [];
                Entities.enemyBullets = [];
            }
        }
        
        Entities.playerShoot();
        
        if (p.invincibleTimer > 0) p.invincibleTimer -= dt;
        
        for (var i = Entities.playerBullets.length - 1; i >= 0; i--) {
            var b = Entities.playerBullets[i];
            b.x += b.vx * dt;
            b.y += b.vy * dt;
            if (b.y < -50 || b.x < -50 || b.x > Engine.width + 50) Entities.playerBullets.splice(i, 1);
        }
        
        for (var i = Entities.enemyBullets.length - 1; i >= 0; i--) {
            var b = Entities.enemyBullets[i];
            b.x += b.vx * dt;
            b.y += b.vy * dt;
            if (b.y > Engine.height + 50 || b.x < -50 || b.x > Engine.width + 50) Entities.enemyBullets.splice(i, 1);
        }
        
        for (var i = Entities.enemies.length - 1; i >= 0; i--) {
            var e = Entities.enemies[i];
            Entities.enemyLogic(e);
            if (e.y > Engine.height + 200 && !e.isBoss) Entities.enemies.splice(i, 1);
        }
        
        for (var i = Entities.powerUps.length - 1; i >= 0; i--) {
            var pu = Entities.powerUps[i];
            pu.y += pu.vy * dt;
            if (pu.y > Engine.height + 50) Entities.powerUps.splice(i, 1);
        }
        
        this.updateParticlesOnly();
        this.handleCollisions();
        
        if (p.hp <= 0) {
            this.endGame();
        }
    },
    
    handleCollisions: function() {
        var p = Entities.player;
        
        for (var bIdx = Entities.playerBullets.length - 1; bIdx >= 0; bIdx--) {
            var b = Entities.playerBullets[bIdx];
            var hit = false;
            
            for (var eIdx = Entities.enemies.length - 1; eIdx >= 0; eIdx--) {
                var e = Entities.enemies[eIdx];
                if (MathUtils.checkCollision(b, e, e.isBoss ? 0.7 : 0.9)) { 
                    var damage = b.dmg || 1;
                    e.hp -= damage;
                    Entities.createExplosion(b.x, b.y, "#ffff00", 3);
                    
                    if (e.hp <= 0) {
                        Engine.score += e.maxHp * 10;
                        Entities.createExplosion(e.x + e.width/2, e.y + e.height/2, e.color, e.isBoss ? 100 : 15);
                        if (!e.isBoss) Entities.dropPowerUp(e.x + e.width/2, e.y + e.height/2);
                        Entities.enemies.splice(eIdx, 1);
                    }
                    hit = true;
                    break; 
                }
            }
            if (hit && b.type !== 'plasma') {
                Entities.playerBullets.splice(bIdx, 1);
            }
        }
        
        if (!p || p.invincibleTimer > 0) return;
        
        for (var i = Entities.enemyBullets.length - 1; i >= 0; i--) {
            var eb = Entities.enemyBullets[i];
    
