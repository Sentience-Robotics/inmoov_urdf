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

#pragma once

#include <gz/msgs/float_v.pb.h>
#include <gz/msgs/int32.pb.h>
#include <gz/msgs/int32_v.pb.h>

#include <mutex>
#include <chrono>
#include <string>
#include <utility>
#include <vector>
#include <memory>

#include <gz/common/Console.hh>
#include <gz/plugin/Register.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/sim/components/Component.hh>
#include <gz/sim/components/Factory.hh>
#include <gz/transport/Node.hh>

#include "OUPressureSensor.hpp"

namespace mock_sensor
{
class MockSensorSystem : public gz::sim::System,
  public gz::sim::ISystemConfigure,
  public gz::sim::ISystemPostUpdate,
  public gz::sim::ISystemPreUpdate
{
private:
  gz::sim::Model model_;

  double voltage_pressed_;
  double voltage_released_;

  gz::transport::Node node_;
  gz::transport::Node::Publisher publisher_;

  std::chrono::nanoseconds update_period_{0};
  std::chrono::nanoseconds last_update_time_{0};

  bool pressed_{false};
  struct Sensor
  {
    std::string name;
    OUPressureSensor model;
    Sensor(const std::string & name, const OUPressureSensor & model)
    : name(std::move(name)), model(std::move(model)) {}
  };
  std::mutex sensor_mutex_;
  std::vector<Sensor> sensors_;

  int keybind_;

public:
  MockSensorSystem() {}
  ~MockSensorSystem() override = default;

  void Configure(
    const gz::sim::Entity & entity,
    const std::shared_ptr<const sdf::Element> & sdf,
    gz::sim::EntityComponentManager & ecm,
    gz::sim::EventManager &) override;

  void OnKeyPress(const gz::msgs::Int32 & msg);

  void PreUpdate(
    const gz::sim::UpdateInfo & _info,
    gz::sim::EntityComponentManager &) override;
  void PostUpdate(
    const gz::sim::UpdateInfo & _info,
    const gz::sim::EntityComponentManager &) override;
};
}  // namespace mock_sensor
