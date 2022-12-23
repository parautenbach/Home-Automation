let widget = await createWidget();
if (!config.runsInWidget) {
    await widget.presentLarge();
}

Script.setWidget(widget);
Script.complete();

async function createWidget() {

    const serverUrl = "https://example.com/";
    const sensorUrl = serverUrl + "api/states/sensor.loadshedding_forecast";
    const iconUrl = serverUrl + "static/icons/favicon-192x192.png";
    const token = "notatoken";
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
    iconWidget.leftAlignImage()

    header.addSpacer(2);

    const title = header.addStack();
    title.setPadding(2, 0, 0, 0);
    const titleText = title.addText("Loadshedding");
    titleText.font = Font.regularSystemFont(30);
    titleText.textColor = Color.black();
    titleText.leftAlignText()

    widget.addSpacer(5)

    const forecast = widget.addStack();
    forecast.setPadding(0, 0, 0, 0);
    forecast.borderWidth = 0;

    const forecastText = forecast.addText(forecastData);
    forecastText.font = Font.regularSystemFont(10);
    forecastText.textColor = Color.black();

    widget.addSpacer(15)

    const lastUpdated = widget.addStack();
    const time = (new Date()).toLocaleTimeString().slice(0, 5);
    const lastUpdatedText = lastUpdated.addText("Last update: " + time);
    lastUpdatedText.font = Font.regularSystemFont(10);
    lastUpdatedText.rightAlignText()
    //let date = new Date();
    //const d = updatedStack.addDate(date);
    //let f = new DateFormatter();
    //d.applyRelativeStyle();
    //updatedStack.addText(" ago");

    return widget;
}

/*
The following function is "borrowed" from:
https://gist.github.com/marco79cgn/23ce08fd8711ee893a3be12d4543f2d2
Retrieves the image from the local file store or downloads it once
*/
async function getIcon(file, imageUrl) {
    let fm = FileManager.local()
    let dir = fm.documentsDirectory()
    let path = fm.joinPath(dir, file)
    if (fm.fileExists(path)) {
        return fm.readImage(path)
    } else {
        let iconImage = await loadImage(imageUrl)
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
