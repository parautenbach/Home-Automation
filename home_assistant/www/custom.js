/*
Idea taken from https://gist.github.com/thomasloven/2a37152725c582fec4420ecedb65ebe3

Add this to your configuration.yaml
frontend:
  extra_module_url:
    - /local/ThemeOverride.js

And put the following into <config-dir>/www/ThemeOverride.js

https://community.home-assistant.io/t/rounded-corners-in-every-theme/103833/6
*/

/*
Also see: https://github.com/home-assistant/frontend/blob/master/src/resources/ha-style.ts
*/

document.documentElement.style.setProperty('--ha-card-border-radius', '5px');
//document.documentElement.style.setProperty('--ha-card-border-color', 'rgba(0,0,0,0)');  // transparent

document.documentElement.style.setProperty('--custom-color-blue',      '#3498db');  // slate: #2980b9 - 2b84d2
document.documentElement.style.setProperty('--custom-color-yellow',    '#ff9800');  // slate: #b58e31 - fd8509
document.documentElement.style.setProperty('--custom-color-red',       '#e74c3c');  // slate: #b83829 - df342e
document.documentElement.style.setProperty('--custom-color-green',     '#70a03c');  // slate: #70a03c - 107001
document.documentElement.style.setProperty('--custom-color-magenta',   '#8840a7');  // slate: #xxxxxx - 8840a7
document.documentElement.style.setProperty('--custom-color-turquoise', '#62a7a0');  // slate: #xxxxxx - 62a7a0
document.documentElement.style.setProperty('--custom-color-gray',      '#cccccc');

document.documentElement.style.setProperty('--mini-media-player-background-opacity', 0.2);
document.documentElement.style.setProperty('--mini-media-player-artwork-opacity',    0.8);

// https://www.home-assistant.io/integrations/frontend/

// setting these here means it will work for both the panel and the history graph cards
document.documentElement.style.setProperty('--state-alarm_control_panel-armed_home-color', '#ffa800');
document.documentElement.style.setProperty('--state-alarm_control_panel-armed_away-color', '#aa0000');
document.documentElement.style.setProperty('--state-alarm_control_panel-disarmed-color',   '#40b100');
document.documentElement.style.setProperty('--state-alarm_control_panel-triggered-color',  '#135dd8');
// do we want to set --state-alarm_control_panel-unavailable-color too? consider light vs dark theme, and unavailable vs unknown

// document.documentElement.style.setProperty('--state-climate-off-color',      '#9e9e9e');
// document.documentElement.style.setProperty('--state-climate-heat-color',     '#ed783b');
// document.documentElement.style.setProperty('--state-climate-cool-color',     '#4892ea');
// document.documentElement.style.setProperty('--state-climate-fan_only-color', '#54b9d1');
