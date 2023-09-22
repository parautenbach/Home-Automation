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

    // key: [resource, label, value, unit]
    const sensors = {
        "soc": ["api/states/sensor.battery_state_of_charge", "Battery", "", "%"],
        "pv": ["api/states/sensor.pv_power_5min_average", "Solar", "", "W"],
        "reserve": ["api/states/sensor.solar_reserve_percentage_5min_average", "Reserve", "", "%"],
        "home": ["api/states/sensor.home_power_5min_average", "Home", "", "W"],
        "grid": ["api/states/binary_sensor.grid_feed", "Grid", "off", ""],
        "utilisation": ["api/states/sensor.solar_energy_utilisation_today", "Utilisation", "", "%"],
        "today": ["api/states/sensor.average_solar_energy_forecast_today", "Today", "", "kWh"],
        "tomorrow": ["api/states/sensor.energy_production_tomorrow", "Tomorrow", "", "kWh"],
        "mode": ["api/states/sensor.charge_mode", "Mode", "", ""]
    };

    const iconUrl = serverUrl + "static/icons/favicon-192x192.png";
    const token = Keychain.get(serverApiTokenKey);
    //console.log(token);
    const colorCode = "#03a9f4";

    const iconImage = await getIcon("hass-favicon.png", iconUrl);

    const sensorData = await getData(serverUrl, token, sensors);
    // console.log(sensors);

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
    parentStack.addSpacer(20);
    let rightStack = parentStack.addStack();
    rightStack.layoutVertically();

    let currentStack = null;
    let sensor = null;

    currentStack = leftStack;
    sensor = sensors["pv"];
    addItem(currentStack, sensor[1], parseInt(sensor[2]).toLocaleString(), sensor[3]);
    sensor = sensors["reserve"];
    addItem(currentStack, sensor[1], sensor[2], sensor[3]);
    sensor = sensors["utilisation"];
    addItem(currentStack, sensor[1], sensor[2], sensor[3]);
    sensor = sensors["today"];
    addItem(currentStack, sensor[1], parseFloat(sensor[2]).toFixed(1), sensor[3]);
    sensor = sensors["tomorrow"];
    addItem(currentStack, sensor[1], parseFloat(sensor[2]).toFixed(1), sensor[3]);

    currentStack = rightStack;
    sensor = sensors["soc"];
    addItem(currentStack, sensor[1], sensor[2], sensor[3]);
    sensor = sensors["mode"];
    addItem(currentStack, sensor[1], sensor[2], sensor[3]);
    sensor = sensors["home"];
    addItem(currentStack, sensor[1], parseInt(sensor[2]).toLocaleString(), sensor[3]);
    sensor = sensors["grid"];
    let gridValue = "";
    let gridValueColor = null;
    if (sensor[2] == "on") {
        gridValue = "Connected";
        gridValueColor = Color.yellow();
    } else {
        gridValue = "Disconnected";
        gridValueColor = Color.lightGray();
    }
    addItem(currentStack, sensor[1], gridValue, sensor[3]);  //, gridValueColor);
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
    let topPoint = new Point(canvasWidth/2, 100);
    let bottomPoint = new Point(canvasWidth/2, canvasHeight - 40);

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

async function getData(serverUrl, token, sensors) {
    for (const [key, values] of Object.entries(sensors)) {
        let req = new Request(serverUrl + values[0])
        // console.log(req);
        req.headers = {
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json"
                      };
        let state = (await req.loadJSON()).state;
        // console.log(state);
        sensors[key][2] = state;
    }
}
