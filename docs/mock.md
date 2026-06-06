# Gazebo plugin and hardware mocking

## MockSensorSystem

You can simulate sensors by using mock_sensor::MockSensorSystem

### Plugin declaration

Declare the plugin with filename and FQN of the class
```xml
<plugin filename="libmock_sensor.so" name="mock_sensor::MockSensorSystem">
```

### Tags

Use the following tags to define the plugin parameters.

| Tags | Type | Description |
|-----------|------|-------------|
| <update_rate> | double | Define the update rate of the plugin |
| <keybind> | int | Define the keybind to trigger sensor on gazebo |
| <voltage_pressed> | double | Define the sensor voltage sent when the sensor is pressed |
| <voltage_released> | double | Define the sensor voltage sent when the sensor is released |
| <sensor> | XML Element | Create a new sensor |

### Sensor declaration

To declare a basic sensor, use <sensor/> tag.
Each sensors uses the Ornstein-Uhlenbeck process to generate values.
Model parameters of the model can be redefined:

| Tags | Type | Default | Description |
|------|------|---------|-------------|
| theta | double | 3.0 | mean reversion speed |
| sigma | double | 3.0 | volatility |
| seed | uint32 | random | Random seed |
