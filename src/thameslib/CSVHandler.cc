/**
@file CSVHandler.cc
@brief Definition of helper functions for handling CSV files
*/

#include "CSVHandler.h"

using std::cout;
using std::endl;
using std::string;

std::istream &operator>>(std::istream &str, CSVRow &data) {
  data.readNextRow(str);
  return str;
}

// Handler functions to convert to different data types
int row2int(const std::string_view &string) {
  int result = std::stoi(std::string(string));
  return (result);
}

double row2double(const std::string_view &string) {
  double result = std::stod(std::string(string));
  return (result);
}
