/*
Idea stolen from https://gist.github.com/thomasloven/2a37152725c582fec4420ecedb65ebe3

Add this to your configuration.yaml
frontend:
  extra_module_url:
    - /local/ThemeOverride.js

And put the following into <config-dir>/www/ThemeOverride.js

https://community.home-assistant.io/t/rounded-corners-in-every-theme/103833/6?u=parautenbach
*/

document.documentElement.style.setProperty('--ha-card-border-radius', '10px');