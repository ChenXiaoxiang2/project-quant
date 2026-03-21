// renderer.js - 高性能炫酷渲染引擎
// 处理所有的 Canvas 绘制，包含星际发光、粒子、机甲外观

var Renderer = {
    draw: function(ctx, width, height) {
        // 1. 清屏与深空背景
        ctx.fillStyle = "#050510";
        ctx.fillRect(0, 0, width, height);
        
        // 2. 绘制星空视差背景
        this.drawStars(ctx, width, height);
        
        // 设置默认融合模式实现发光特效
        ctx.globalCompositeOperation = "lighter";
        
        // 3. 绘制道具
        this.drawPowerUps(ctx);
        
        // 4. 绘制粒子(爆炸效果)
        this.drawParticles(ctx);
        
        // 5. 绘制敌机子弹
        this.drawEnemyBullets(ctx);
        
        // 6. 绘制玩家子弹
        this.drawPlayerBullets(ctx);
        
        // 恢复正常融合模式绘制实体机甲
        ctx.globalCompositeOperation = "source-over";
        
        // 7. 绘制敌机
        this.drawEnemies(ctx);
        
        // 8. 绘制玩家机体
        this.drawPlayer(ctx);
        
        // 9. 更新 HTML HUD UI
        this.updateHUD();
    },
    
    drawStars: function(ctx, width, height) {
        ctx.fillStyle = "#ffffff";
        var dt = Engine.deltaTime;
        
        for (var i = 0; i < Entities.stars.length; i++) {
            var s = Entities.stars[i];
            s.y += s.speed * dt;
            if (s.y > height) {
                s.y = 0;
                s.x = Math.random() * width;
            }
            // 闪烁效果
            s.brightness += MathUtils.randomRange(-0.05, 0.05);
            if (s.brightness < 0.2) s.brightness = 0.2;
            if (s.brightness > 1) s.brightness = 1;
            
            ctx.globalAlpha = s.brightness;
            ctx.beginPath();
            ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1.0;
    },
    
    drawParticles: function(ctx) {
        for (var i = 0; i < Entities.particles.length; i++) {
            var p = Entities.particles[i];
            var ratio = p.life / p.maxLife;
            ctx.globalAlpha = ratio;
            ctx.fillStyle = p.color;
            ctx.shadowBlur = 10;
            ctx.shadowColor = p.color;
            
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size * ratio, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.shadowBlur = 0;
        ctx.globalAlpha = 1.0;
    },
    
    drawPowerUps: function(ctx) {
        for (var i = 0; i < Entities.powerUps.length; i++) {
            var p = Entities.powerUps[i];
            ctx.fillStyle = p.color;
            ctx.shadowBlur = 15;
            ctx.shadowColor = p.color;
            
            ctx.beginPath();
            ctx.arc(p.x + p.width/2, p.y + p.height/2, p.width/2, 0, Math.PI * 2);
            ctx.fill();
            
            // 核心高光
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.arc(p.x + p.width/2, p.y + p.height/2, p.width/4, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.shadowBlur = 0;
    },
    
    drawPlayerBullets: function(ctx) {
        for (var i = 0; i < Entities.playerBullets.length; i++) {
            var b = Entities.playerBullets[i];
            if (b.type === 'laser') {
                ctx.fillStyle = "#00ffff";
                ctx.shadowBlur = 15;
                ctx.shadowColor = "#00ffff";
                ctx.fillRect(b.x, b.y, b.width, b.height);
            } else if (b.type === 'plasma') {
                ctx.fillStyle = "#ffffff";
                ctx.shadowBlur = 20;
                ctx.shadowColor = "#0055ff";
                ctx.beginPath();
                ctx.arc(b.x + b.width/2, b.y + b.height/2, b.width/2, 0, Math.PI*2);
                ctx.fill();
            }
        }
        ctx.shadowBlur = 0;
    },
    
    drawEnemyBullets: function(ctx) {
        for (var i = 0; i < Entities.enemyBullets.length; i++) {
            var b = Entities.enemyBullets[i];
            ctx.fillStyle = b.color;
            ctx.shadowBlur = 10;
            ctx.shadowColor = b.color;
            // 绘制带有棱角的子弹 (菱形)
            ctx.beginPath();
            ctx.moveTo(b.x + b.width/2, b.y);
            ctx.lineTo(b.x + b.width, b.y + b.height/2);
            ctx.lineTo(b.x + b.width/2, b.y + b.height);
            ctx.lineTo(b.x, b.y + b.height/2);
            ctx.closePath();
            ctx.fill();
        }
        ctx.shadowBlur = 0;
    },
    
    drawEnemies: function(ctx) {
        for (var i = 0; i < Entities.enemies.length; i++) {
            var e = Entities.enemies[i];
            ctx.fillStyle = e.color;
            var cx = e.x + e.width/2;
            var cy = e.y + e.height/2;
            
            if (e.type === "scout") {
                // 箭头形侦察机
                ctx.beginPath();
                ctx.moveTo(cx, e.y + e.height);
                ctx.lineTo(e.x + e.width, e.y);
                ctx.lineTo(cx, e.y + e.height/4);
                ctx.lineTo(e.x, e.y);
                ctx.closePath();
                ctx.fill();
            } else if (e.type === "fighter") {
                // 经典战机形
                ctx.beginPath();
                ctx.moveTo(cx, e.y + e.height);
                ctx.lineTo(e.x + e.width, e.y + e.height*0.2);
                ctx.lineTo(e.x + e.width*0.8, e.y);
                ctx.lineTo(e.x + e.width*0.2, e.y);
                ctx.lineTo(e.x, e.y + e.height*0.2);
                ctx.closePath();
                ctx.fill();
            } else if (e.type === "cruiser") {
                // 重型巡洋舰，正六边形风格
                ctx.beginPath();
                ctx.moveTo(cx, e.y + e.height);
                ctx.lineTo(e.x + e.width, e.y + e.height*0.7);
                ctx.lineTo(e.x + e.width, e.y + e.height*0.3);
                ctx.lineTo(cx, e.y);
                ctx.lineTo(e.x, e.y + e.height*0.3);
                ctx.lineTo(e.x, e.y + e.height*0.7);
                ctx.closePath();
                ctx.fill();
            }
            
            // 绘制血条 (Cruiser 等血量多于基础的才显示)
            if (e.maxHp > 2) {
                var hpRatio = e.hp / e.maxHp;
                ctx.fillStyle = "#ff0000";
                ctx.fillRect(e.x, e.y - 10, e.width, 4);
                ctx.fillStyle = "#00ff00";
                ctx.fillRect(e.x, e.y - 10, e.width * hpRatio, 4);
            }
        }
    },
    
    drawPlayer: function(ctx) {
        var p = Entities.player;
        if (!p) return;
        
        // 无敌闪烁特效
        if (p.invincibleTimer > 0) {
            if (Math.floor(p.invincibleTimer * 10) % 2 === 0) return; 
        }
        
        var cx = p.x + p.width/2;
        var cy = p.y + p.height/2;
        
        // 绘制高科技战机
        ctx.fillStyle = "#ffffff";
        ctx.shadowBlur = 20;
        ctx.shadowColor = "#0088ff";
        
        // 主机体
        ctx.beginPath();
        ctx.moveTo(cx, p.y);                 // 机鼻
        ctx.lineTo(p.x + p.width, p.y + p.height); // 右翼底
        ctx.lineTo(cx, p.y + p.height * 0.8); // 尾部中心凹槽
        ctx.lineTo(p.x, p.y + p.height);     // 左翼底
        ctx.closePath();
        ctx.fill();
        
        // 核心反应堆发光点
        ctx.fillStyle = "#00ffff";
        ctx.beginPath();
        ctx.arc(cx, p.y + p.height * 0.6, 6, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.shadowBlur = 0;
        
        // 尾部引擎喷射火焰 (动态缩放)
        var thrust = MathUtils.randomRange(10, 25);
        ctx.fillStyle = "#00aaff";
        ctx.beginPath();
        ctx.moveTo(cx - 8, p.y + p.height * 0.8);
        ctx.lineTo(cx + 8, p.y + p.height * 0.8);
        ctx.lineTo(cx, p.y + p.height * 0.8 + thrust);
        ctx.closePath();
        ctx.fill();
        
        // 擦弹核心区可视化 (辅助玩家)
        ctx.fillStyle = "rgba(255, 0, 50, 0.4)";
        ctx.beginPath();
        var hitboxRadius = (Math.min(p.width, p.height) / 2) * 0.35;
        ctx.arc(cx, cy, hitboxRadius, 0, Math.PI * 2);
        ctx.fill();
    },
    
    updateHUD: function() {
        var p = Entities.player;
        document.getElementById("scoreDisplay").innerText = "分数: " + Engine.score;
        document.getElementById("healthDisplay").innerText = "装甲: " + (p ? Math.max(0, p.hp) : 0) + "%";
        var weaponName = Entities.WEAPON_TYPES[Math.min(p ? p.weaponLevel : 0, Entities.WEAPON_TYPES.length - 1)];
        document.getElementById("weaponDisplay").innerText = "主炮: " + weaponName;
    }
};