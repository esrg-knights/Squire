//
//  Code adjusted based of Animated Button codepen as found here:
//  https://codepen.io/zanewesley/pen/yLgPEON
//

/*
    SETUP instructions
    1)  Canvas with style attributes:
        position: absolute; top: 0; left: 0; pointer-events: none; height: 100vh;

    2)  Element #confettiButton with onClick=launchConfetti()

    Customisation through button data attributes:
    - colors *optional
        Set front and back colors in pairs of two HTML colors seperated with comma. Eg:
        data-colors="#FF0000,#AA0000,#F5F500,#A5A500"
 */


const button = $('#confettibutton');
var disabled = false;
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

// add Confetti/Sequince objects to arrays to draw them
let confetti = [];
let sequins = [];

// ammount to add on each button press
const confettiCount = 20;
const sequinCount = 10;

// "physics" variables
const gravityConfetti = 0.3;
const gravitySequins = 0.55;
const dragConfetti = 0.075;
const dragSequins = 0.02;
const terminalVelocity = 3;

// colors, back side is darker for confetti flipping
let colors = [];
if (button.data('colors')) {
    var colorstrings = button.data('colors').split(',')
    for (let i = 0; i < colorstrings.length; i+=2){
        colors.push({
            front : colorstrings[i],
            back : colorstrings[i+1]
        });
    }
}
else {
    colors = [
        { front : '#0A3313', back: '#198030' },
        { front : '#10B50B', back: '#10680B' },
        { front : '#33790A', back: '#33400A' }
    ];
}

// helper function to pick a random number within a range
randomRange = (min, max) => Math.random() * (max - min) + min;

// helper function to get initial velocities for confetti
// this weighted spread helps the confetti look more realistic
initConfettoVelocity = (xRange, yRange) => {
    const x = randomRange(xRange[0], xRange[1]);
    const range = yRange[1] - yRange[0] + 1;
    let y = yRange[1] - Math.abs(randomRange(0, range) + randomRange(0, range) - range);
    if (y >= yRange[1] - 1) {
        // Occasional confetto goes higher than the max
        y += (Math.random() < .25) ? randomRange(1, 3) : 0;
    }
    return {x: x, y: -y};
}

// Confetto Class
function Confetto(x_c, x_var, y_c, y_var) {
    this.randomModifier = randomRange(0, 99);
    this.color = colors[Math.floor(randomRange(0, colors.length))];
    this.dimensions = {
        x: randomRange(5, 9),
        y: randomRange(8, 15),
    };
    this.position = {
        x: randomRange(x_c - x_var, x_c + x_var),
        y: randomRange(y_c - y_var, y_c + y_var),
    };
    this.rotation = randomRange(0, 2 * Math.PI);
    this.scale = {
        x: 1,
        y: 1,
    };
    this.velocity = initConfettoVelocity([-9, 9], [6, 11]);
};

Confetto.prototype.update = function() {
    // apply forces to velocity
    this.velocity.x -= this.velocity.x * dragConfetti;
    this.velocity.y = Math.min(this.velocity.y + gravityConfetti, terminalVelocity);
    this.velocity.x += Math.random() > 0.5 ? Math.random() : -Math.random();

    // set position
    this.position.x += this.velocity.x;
    this.position.y += this.velocity.y;

    // spin confetto by scaling y and set the color, .09 just slows cosine frequency
    this.scale.y = Math.cos((this.position.y + this.randomModifier) * 0.09);
}

// Sequin Class
function Sequin(x_c, x_var, y_c, y_var) {
    this.color = colors[Math.floor(randomRange(0, colors.length))].back,
        this.radius = randomRange(1, 2),
        this.position = {
            x: randomRange(x_c - x_var, x_c + x_var),
            y: randomRange(y_c - y_var, y_c + y_var),
        },
        this.velocity = {
            x: randomRange(-6, 6),
            y: randomRange(-8, -12)
        }
}
Sequin.prototype.update = function() {
    // apply forces to velocity
    this.velocity.x -= this.velocity.x * dragSequins;
    this.velocity.y = this.velocity.y + gravitySequins;

    // set position
    this.position.x += this.velocity.x;
    this.position.y += this.velocity.y;
};

// add elements to arrays to be drawn
initBurst = () => {
    var x_c = button.position().left + button.width() / 2;
    var y_c = button.position().top;
    var x_var = button.width()/2;
    var y_var =0;

    for (let i = 0; i < confettiCount; i++) {
        confetti.push(new Confetto(x_c, x_var, y_c, y_var));
    }
    for (let i = 0; i < sequinCount; i++) {
        sequins.push(new Sequin(x_c, x_var, y_c, y_var));
    }
}

// draws the elements on the canvas
render = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    confetti.forEach((confetto, index) => {
        let width = (confetto.dimensions.x * confetto.scale.x);
        let height = (confetto.dimensions.y * confetto.scale.y);

        // move canvas to position and rotate
        ctx.translate(confetto.position.x, confetto.position.y);
        ctx.rotate(confetto.rotation);

        // update confetto "physics" values
        confetto.update();

        // get front or back fill color
        ctx.fillStyle = confetto.scale.y > 0 ? confetto.color.front : confetto.color.back;

        // draw confetto
        ctx.fillRect(-width / 2, -height / 2, width, height);

        // reset transform matrix
        ctx.setTransform(1, 0, 0, 1, 0, 0);
    })

    sequins.forEach((sequin, index) => {
        // move canvas to position
        ctx.translate(sequin.position.x, sequin.position.y);

        // update sequin "physics" values
        sequin.update();

        // set the color
        ctx.fillStyle = sequin.color;

        // draw sequin
        ctx.beginPath();
        ctx.arc(0, 0, sequin.radius, 0, 2 * Math.PI);
        ctx.fill();

        // reset transform matrix
        ctx.setTransform(1, 0, 0, 1, 0, 0);
    })

    // remove confetti and sequins that fall off the screen
    // must be done in seperate loops to avoid noticeable flickering
    confetti.forEach((confetto, index) => {
        if (confetto.position.y >= canvas.height) confetti.splice(index, 1);
    });
    sequins.forEach((sequin, index) => {
        if (sequin.position.y >= canvas.height) sequins.splice(index, 1);
    });

    window.requestAnimationFrame(render);
}

// Block button temporary
launchConfetti = () => {
    if (!disabled) {
        disabled = true;
        window.initBurst();
        setTimeout(() => {
            disabled = false;
    }, 200);
    }
}

// re-init canvas if the window size changes
resizeCanvas = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    cx = ctx.canvas.width / 2;
    cy = ctx.canvas.height / 2;
}

// resize listenter
window.addEventListener('resize', () => {
    resizeCanvas();
});

// click button on spacebar or return keypress
document.body.onkeyup = (e) => {
    if (e.keyCode == 13 || e.keyCode == 32) {
        clickButton();
    }
}

// kick off the render loop
render();
