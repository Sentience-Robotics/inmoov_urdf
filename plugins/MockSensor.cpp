// Copyright 2025 Sentience Robotics Team
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

#include "MockSensor.hpp"

#include <gz/msgs/float_v.pb.h>
#include <gz/msgs/int32.pb.h>
#include <gz/msgs/int32_v.pb.h>

#include <chrono>
#include <mutex>

#include <gz/common/Console.hh>
#include <gz/plugin/Register.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/transport/Node.hh>

namespace mock_sensor
{
void MockSensorSystem::Configure(
  const gz::sim::Entity & entity,
  const std::shared_ptr<const sdf::Element> & sdf,
  gz::sim::EntityComponentManager & ecm,
  gz::sim::EventManager &)
{
  model_ = gz::sim::Model(entity);
  auto modelname = model_.Name(ecm);

  voltage_pressed_ = sdf->Get<double>("voltage_pressed", 4000.0).first;
  voltage_released_ = sdf->Get<double>("voltage_released", 100.0).first;

  std::string topicname = "/" + modelname + "/mock_sensor_data";
  if (sdf && sdf->HasElement("topic_name")) {
    topicname = sdf->Get<std::string>("topic_name");
  }
  publisher_ = node_.Advertise<gz::msgs::Float_V>(topicname);

  double update_rate = 1.0;
  if (sdf && sdf->HasElement("update_rate")) {
    update_rate = sdf->Get<double>("update_rate");
  }

  if (update_rate > 0) {
    std::chrono::duration<double> period(1. / update_rate);
    update_period_ =
      std::chrono::duration_cast<std::chrono::nanoseconds>(period);
  }

  if (sdf && sdf->HasElement("sensor")) {
    auto sensorElem = sdf->FindElement("sensor");
    while (sensorElem) {
      auto thetaElem = sensorElem->Get<double>("theta", 3.0);
      if (!thetaElem.second) {gzwarn << "Fail to parse theta value" << std::endl;}
      auto sigmaElem = sensorElem->Get<double>("sigma", 3.0);
      if (!sigmaElem.second) {gzwarn << "Fail to parse sigma value" << std::endl;}
      std::string name = sensorElem->Get<std::string>("name", "sensor").first;
      uint32_t seed = (sensorElem->HasElement("seed")) ?
        sensorElem->Get<uint32_t>("seed") :
        std::random_device{}();

      sensors_.emplace_back(
        name, OUPressureSensor(100, thetaElem.first, sigmaElem.first, seed));
      sensorElem = sensorElem->GetNextElement("sensor");
    }
  }

  node_.Subscribe("/keyboard/keypress", &MockSensorSystem::OnKeyPress, this);
  keybind_ = sdf->Get("keybind", 83).first;
}

void MockSensorSystem::OnKeyPress(const gz::msgs::Int32 & msg)
{
  if (msg.data() == keybind_) {
    pressed_ = !pressed_;
  }
}

void MockSensorSystem::PreUpdate(
  const gz::sim::UpdateInfo & _info,
  gz::sim::EntityComponentManager & _ecm)
{
  std::lock_guard lock(sensor_mutex_);
  for (auto & sensor : sensors_) {
    sensor.model.setTarget((pressed_) ? voltage_pressed_ : voltage_released_);
  }
}

void MockSensorSystem::PostUpdate(
  const gz::sim::UpdateInfo & _info,
  const gz::sim::EntityComponentManager &)
{
  if (_info.paused) {return;}
  auto elapsed = _info.simTime - last_update_time_;
  if (elapsed < update_period_) {return;}

  double dt = std::chrono::duration<double>(elapsed).count();

  gz::msgs::Float_V msg;
  msg.mutable_header()->mutable_stamp()->set_sec(
    std::chrono::duration_cast<std::chrono::seconds>(_info.simTime).count());
  {
    std::lock_guard lock(sensor_mutex_);
    for (auto & sensor : sensors_) {
      float value = sensor.model.update(dt);
      msg.add_data(value);
    }
  }

  publisher_.Publish(msg);
  last_update_time_ = _info.simTime;
}
}  // namespace mock_sensor

GZ_ADD_PLUGIN(
  mock_sensor::MockSensorSystem, gz::sim::System,
  gz::sim::ISystemConfigure, gz::sim::ISystemPreUpdate,
  gz::sim::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(
  mock_sensor::MockSensorSystem,
  "mock_sensor::MockSensorSystem")
