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

#include <algorithm>
#include <random>

class OUPressureSensor
{
private:
  double target_;
  double theta_;
  double sigma_;

  double pressure_;

  std::mt19937 generator_;
  std::normal_distribution<double> distribution_;

public:
  explicit OUPressureSensor(
    double target, double theta, double sigma,
    uint32_t seed = std::random_device{}())
  : target_(target),
    theta_(theta),
    sigma_(sigma),
    pressure_(target),
    generator_(seed) {}
  ~OUPressureSensor() = default;

  double update(double dt)
  {
    distribution_ = std::normal_distribution(0.0, std::sqrt(dt));

    double dW = distribution_(generator_);
    double rappel = theta_ * (target_ - pressure_) * dt;
    double perturbation = sigma_ * dW;
    pressure_ = pressure_ + rappel + perturbation;
    pressure_ = std::max(pressure_, 0.);

    return pressure_;
  }

  void setTarget(double value) {target_ = value;}
};
