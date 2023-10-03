// credit: https://gist.github.com/m33x/62f6e8f6eab546e4b3a854695ea8c3a8
// set this true and run from the app the first time and then make it false
const setup = false;

const serverHostPortKey = "HA Host";
const serverApiTokenKey = "HA API Token";

if (setup) {
    await setupCredentials();
}

const widget = await createWidget();

if (!config.runsInWidget) {
    await widget.presentMedium();
}

Script.setWidget(widget);
Script.complete();

async function captureCredential(key, exampleValue) {
    if (Keychain.contains(key)) {
        Keychain.remove(key);
    }
    const alert = new Alert();
    alert.title = key;
    alert.addSecureTextField(exampleValue, "");
    await alert.presentAlert();
    const value = alert.textFieldValue(0);
    Keychain.set(key, value);
}

async function setupCredentials() {
    await captureCredential(serverHostPortKey, "example.com:8123");
    await captureCredential(serverApiTokenKey, "token");
}

async function createWidget() {
    // https://talk.automators.fm/t/how-to-store-credentials-securely-drafts-5-credential-equivalent/1619
    const serverUrl = "https://" + Keychain.get(serverHostPortKey) + "/";
    //console.log(serverUrl);

    const resource = "api/states/sensor.resource_widget";
    // key: [label, value, unit]
    const sensor_map = {
        "battery_state_of_charge": ["Battery", "", "%"],
        "pv_power": ["Solar", "", "W"],
        "solar_reserve_percentage": ["Reserve", "", "%"],
        "home_power": ["Home", "", "W"],
        "grid_feed": ["Grid", "", ""],
        "solar_energy_utilisation_today": ["Utilisation", "", "%"],
        "solar_energy_forecast_today": ["Today", "", "kWh"],
        "solar_energy_forecast_tomorrow": ["Tomorrow", "", "kWh"],
        "charge_mode": ["Mode", "", ""]
    };

    const iconUrl = serverUrl + "static/icons/favicon-192x192.png";
    const token = Keychain.get(serverApiTokenKey);
    //console.log(token);
    const colorCode = "#03a9f4";

    const iconImage = await getIcon("hass-favicon.png", iconUrl);

    const sensorData = await getData(serverUrl, resource, token, sensor_map);

    const widget = new ListWidget();
    widget.backgroundColor = new Color(colorCode, 1.0);
    widget.url = "homeassistant://navigate/lovelace/resources";

    const header = widget.addStack();

    const icon = header.addStack();
    icon.backgroundColor = new Color(colorCode, 1.0)
    icon.cornerRadius = 1
    const iconWidget = icon.addImage(iconImage)
    iconWidget.imageSize = new Size(30, 30)

    header.addSpacer(2);

    const title = header.addStack();
    title.setPadding(2, 0, 0, 0);
    const titleText = title.addText("Energy");
    titleText.font = Font.regularSystemFont(20);
    titleText.textColor = Color.white();

    let parentStack = widget.addStack();
    parentStack.layoutHorizontally();
    let leftStack = parentStack.addStack();
    leftStack.layoutVertically();
    parentStack.addSpacer(30);
    let rightStack = parentStack.addStack();
    rightStack.layoutVertically();

    let currentStack = null;
    let sensor = null;

    currentStack = leftStack;
    sensor = sensor_map["pv_power"];
    // only the sensors that track mean values need the conditional check
    // tl;dr: no samples => no statistic => unknown
    // https://github.com/home-assistant/core/issues/58748
    // https://community.home-assistant.io/t/why-does-this-statistics-sensor-have-an-unknown-state/320632
    addItem(currentStack, sensor[0], parseInt((sensor[1] === "unknown") ? 0 : sensor[1]).toLocaleString(), sensor[2]);
    sensor = sensor_map["solar_reserve_percentage"];
    addItem(currentStack, sensor[0], (sensor[1] === "unknown" || sensor[1] === "unavailable") ? 0 : sensor[1], sensor[2]);
    sensor = sensor_map["solar_energy_utilisation_today"];
    addItem(currentStack, sensor[0], sensor[1], sensor[2]);
    sensor = sensor_map["solar_energy_forecast_today"];
    addItem(currentStack, sensor[0], parseFloat(sensor[1]).toFixed(1), sensor[2]);
    sensor = sensor_map["solar_energy_forecast_tomorrow"];
    addItem(currentStack, sensor[0], parseFloat(sensor[1]).toFixed(1), sensor[2]);

    currentStack = rightStack;
    sensor = sensor_map["battery_state_of_charge"];
    addItem(currentStack, sensor[0], sensor[1], sensor[2]);
    sensor = sensor_map["charge_mode"];
    addItem(currentStack, sensor[0], sensor[1], sensor[2]);
    sensor = sensor_map["home_power"];
    addItem(currentStack, sensor[0], parseInt((sensor[1] === "unknown") ? 0 : sensor[1]).toLocaleString(), sensor[2]);
    sensor = sensor_map["grid_feed"];
    let gridValue = "";
    let gridValueColor = null;
    if (sensor[1] == "on") {
        gridValue = "Connected";
        gridValueColor = Color.yellow();
    } else {
        gridValue = "Disconnected";
        gridValueColor = Color.lightGray();
    }
    addItem(currentStack, sensor[0], gridValue, sensor[2]);  //, gridValueColor);
    const time = (new Date()).toLocaleTimeString().slice(0, 5);
    addItem(currentStack, "Last update", time, "");

    // for (const [key, values] of Object.entries(sensors)) {
    //     widget.addSpacer(5);
    //     const stack = widget.addStack();
    //     stack.setPadding(0, 0, 0, 0);
    //     stack.borderWidth = 0;
    //     const stackText = stack.addText(values[1] + ": " + values[2] + values[3]);
    //     stackText.font = Font.regularSystemFont(14);
    //     stackText.textColor = Color.white();
    // }

    // widget.addSpacer(3)
    // const lastUpdated = rightStack.addStack();
    // const time = (new Date()).toLocaleTimeString().slice(0, 5);
    // const lastUpdatedText = lastUpdated.addText("Last update: " + time);
    // lastUpdatedText.font = Font.regularSystemFont(12);
    // lastUpdatedText.rightAlignText()
    // lastUpdatedText.textColor = Color.white();

    const lineWeight = 5;
    const lineColor = Color.white();
    const canvasHeight = 338;
    const canvasWidth = 720;
    let drawContext = new DrawContext();
    drawContext.size = new Size(canvasWidth, canvasHeight);
    drawContext.opaque = false;
    let topPoint = new Point(canvasWidth/2, 110);
    let bottomPoint = new Point(canvasWidth/2, canvasHeight - 35);

    const path = new Path();
    path.move(topPoint);
    path.addLine(bottomPoint);
    drawContext.addPath(path);
    drawContext.setStrokeColor(lineColor);
    drawContext.setLineWidth(lineWeight);
    drawContext.strokePath();

    widget.backgroundImage = (drawContext.getImage());

    return widget;
}

function addItem(widget, label, value, unit, valueColor) {
    widget.addSpacer(3);
    const labelStack = widget.addStack();
    labelStack.setPadding(0, 0, 0, 0);
    labelStack.borderWidth = 0;
    const labelStackText = labelStack.addText(label + ": ");
    labelStackText.font = Font.boldSystemFont(12);
    labelStackText.textColor = Color.white();

    const valueStack = widget.addStack();
    valueStack.setPadding(0, 0, 0, 0);
    valueStack.borderWidth = 0;
    const valueStackText = labelStack.addText(value + unit);
    valueStackText.font = Font.regularSystemFont(12);
    if (valueColor === undefined) {
        valueStackText.textColor = Color.white();
    } else {
        valueStackText.textColor = valueColor;
    }
}

/*
The following function is "borrowed" from:
https://gist.github.com/marco79cgn/23ce08fd8711ee893a3be12d4543f2d2
Retrieves the image from the local file store or downloads it once
*/
async function getIcon(file, imageUrl) {
    const fm = FileManager.local();
    const dir = fm.documentsDirectory();
    const path = fm.joinPath(dir, file);
    if (fm.fileExists(path)) {
        return fm.readImage(path)
    } else {
        const iconImage = await loadImage(imageUrl)
        fm.writeImage(path, iconImage);
        return iconImage;
    }
}

/*
The following function is "borrowed" from:
https://gist.github.com/marco79cgn/23ce08fd8711ee893a3be12d4543f2d2
Downloads an image from a given URL
*/
async function loadImage(imgUrl) {
    const req = new Request(imgUrl)
    return await req.loadImage()
}

async function getData(serverUrl, resource, token, sensor_map) {
    let req = new Request(serverUrl + resource)
    // console.log(req);
    req.headers = {
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json"
                  };
    let state = (await req.loadJSON());
    // console.log(state);
    for (const [key, values] of Object.entries(sensor_map)) {
        sensor_map[key][1] = state.attributes[key];
    }
    // console.log(sensor_map);
}
