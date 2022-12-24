// set this true and run from the app the first time and then make it false
const setup = false;

const serverHostPortKey = "HA Host";
const serverApiTokenKey = "HA API Token";

if (setup) {
    await setupCredentials();
}

const widget = await createWidget();

if (!config.runsInWidget) {
    await widget.presentLarge();
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
    const sensorUrl = serverUrl + "api/states/sensor.loadshedding_forecast";
    const iconUrl = serverUrl + "static/icons/favicon-192x192.png";
    const token = Keychain.get(serverApiTokenKey);
    //console.log(token);
    const colorCode = "#03a9f4";

    const iconImage = await getIcon("hass-favicon.png", iconUrl);
    const sensorData = await getData(sensorUrl, token);
    const forecastData = sensorData['state'];

    const widget = new ListWidget();
    widget.backgroundColor = new Color(colorCode, 1.0);
    widget.url = "homeassistant://navigate/lovelace/main";

    const header = widget.addStack();

    const icon = header.addStack();
    icon.backgroundColor = new Color(colorCode, 1.0)
    icon.cornerRadius = 1
    const iconWidget = icon.addImage(iconImage)
    iconWidget.imageSize = new Size(40, 40)

    header.addSpacer(2);

    const title = header.addStack();
    title.setPadding(2, 0, 0, 0);
    const titleText = title.addText("Loadshedding");
    titleText.font = Font.regularSystemFont(30);

    widget.addSpacer(5)

    const forecast = widget.addStack();
    forecast.setPadding(0, 0, 0, 0);
    forecast.borderWidth = 0;

    const forecastText = forecast.addText(forecastData);
    forecastText.font = Font.regularSystemFont(14);

    widget.addSpacer(15)

    const lastUpdated = widget.addStack();
    const time = (new Date()).toLocaleTimeString().slice(0, 5);
    const lastUpdatedText = lastUpdated.addText("Last update: " + time);
    lastUpdatedText.font = Font.regularSystemFont(8);
    lastUpdatedText.rightAlignText()

    return widget;
}

/*
The following function is "borrowed" from:
https://gist.github.com/marco79cgn/23ce08fd8711ee893a3be12d4543f2d2
Retrieves the image from the local file store or downloads it once
*/
async function getIcon(file, imageUrl) {
    const fm = FileManager.local()
    const dir = fm.documentsDirectory()
    const path = fm.joinPath(dir, file)
    if (fm.fileExists(path)) {
        return fm.readImage(path)
    } else {
        const iconImage = await loadImage(imageUrl)
        fm.writeImage(path, iconImage)
        return iconImage
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

async function getData(serverUrl, token) {
    let req = new Request(serverUrl)
    req.headers = {
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json"
                  }
    return await req.loadJSON();
}
