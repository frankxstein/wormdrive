// wormdrive robot firmware scaffold — ESP32 (Arduino framework)
//
// STATUS: SCAFFOLD. This sketch has NOT been compiled on real hardware or
// tested on a physical board. Pin numbers, PWM configuration, and motor
// driver wiring are placeholders that MUST be adapted to your robot before
// use. It exists to document the expected packet handling and, most
// importantly, the receiver-side watchdog contract.
//
// Contract with the PC side (see docs/ARCHITECTURE.md):
//  - Listens for JSON motor packets on UDP: {"type":"motor","left":..,"right":..,"frame":..}
//  - left/right are in [-1.0, 1.0]
//  - MUST zero the motors if no valid packet arrives for WATCHDOG_MS
//  - Periodically sends IMU telemetry back: {"type":"imu","yaw_rate":..}

#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

// ---- CONFIGURE ME ----------------------------------------------------------
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASS = "YOUR_PASSWORD";
const uint16_t LISTEN_PORT = 9000;   // must match robot_port in config.yaml
const uint16_t PC_PORT     = 9001;   // must match pc_port in config.yaml
IPAddress pcAddress(192, 168, 1, 10); // set to your PC's LAN address

const int LEFT_PWM_PIN   = 25;  // placeholder
const int LEFT_DIR_PIN   = 26;  // placeholder
const int RIGHT_PWM_PIN  = 27;  // placeholder
const int RIGHT_DIR_PIN  = 14;  // placeholder

const unsigned long WATCHDOG_MS  = 500;  // zero motors after this much silence
const unsigned long TELEMETRY_MS = 50;   // IMU send interval
// ----------------------------------------------------------------------------

WiFiUDP udp;
unsigned long lastValidPacketMs = 0;
unsigned long lastTelemetryMs = 0;

void setMotors(float left, float right) {
  // Placeholder differential-drive output. Adapt to your motor driver
  // (e.g. DRV8833/L298N direction pin + PWM duty). Values in [-1, 1].
  left  = constrain(left,  -1.0f, 1.0f);
  right = constrain(right, -1.0f, 1.0f);

  digitalWrite(LEFT_DIR_PIN,  left  >= 0 ? HIGH : LOW);
  digitalWrite(RIGHT_DIR_PIN, right >= 0 ? HIGH : LOW);
  analogWrite(LEFT_PWM_PIN,  (int)(fabsf(left)  * 255));
  analogWrite(RIGHT_PWM_PIN, (int)(fabsf(right) * 255));
}

void stopMotors() { setMotors(0.0f, 0.0f); }

float readYawRate() {
  // Placeholder: return gyro Z from your IMU (e.g. MPU6050 over I2C),
  // in rad/s. Returning 0 until an IMU is wired up.
  return 0.0f;
}

void setup() {
  Serial.begin(115200);
  pinMode(LEFT_PWM_PIN, OUTPUT);
  pinMode(LEFT_DIR_PIN, OUTPUT);
  pinMode(RIGHT_PWM_PIN, OUTPUT);
  pinMode(RIGHT_DIR_PIN, OUTPUT);
  stopMotors();

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.printf("\nIP: %s\n", WiFi.localIP().toString().c_str());
  udp.begin(LISTEN_PORT);
  lastValidPacketMs = millis();
}

void loop() {
  // 1) Receive motor commands
  int packetSize = udp.parsePacket();
  if (packetSize > 0) {
    char buf[256];
    int len = udp.read(buf, sizeof(buf) - 1);
    if (len > 0) {
      buf[len] = '\0';
      StaticJsonDocument<192> doc;
      DeserializationError err = deserializeJson(doc, buf);
      // Reject malformed or mistyped packets — same policy as the PC side.
      if (!err && doc["type"] == "motor"
          && doc["left"].is<float>() && doc["right"].is<float>()) {
        setMotors(doc["left"].as<float>(), doc["right"].as<float>());
        lastValidPacketMs = millis();
      }
    }
  }

  // 2) Watchdog: this is the safety-critical part of the contract.
  if (millis() - lastValidPacketMs > WATCHDOG_MS) {
    stopMotors();
  }

  // 3) Telemetry
  if (millis() - lastTelemetryMs > TELEMETRY_MS) {
    lastTelemetryMs = millis();
    StaticJsonDocument<96> doc;
    doc["type"] = "imu";
    doc["yaw_rate"] = readYawRate();
    char out[96];
    size_t n = serializeJson(doc, out, sizeof(out));
    udp.beginPacket(pcAddress, PC_PORT);
    udp.write((const uint8_t*)out, n);
    udp.endPacket();
  }
}
