/**
@file utils.h
@brief Define some simple utility functions.
*/
#ifndef SRC_THAMESLIB_UTILS_H_
#define SRC_THAMESLIB_UTILS_H_

#include "global.h"

/**
@brief Convert an STL string into a given data type.

@param t is the new data type variable that will hold the value
@param s is the string to convert
@return true if the conversion was successful, false otherwise
*/
template <class T> bool from_string(T &t, const std::string &s) {
  std::istringstream iss(s, std::istringstream::in);
  return !(iss >> t).fail();
}

/**
@brief Convert any data type to a string.

@param t is the input data
@return the string that was created to hold the data
*/
template <class T> std::string to_string(const T &t) {
  std::ostringstream oss;
  oss << t;
  return oss.str();
}

///
/// The methods below are NOT USED.
///

namespace utils {

  void replace(std::string &where, const std::string &what,
               const std::string &by);

  bool start_with(const std::string &str, const std::string &what);
  bool end_with(const std::string &str, const std::string &what);

} // namespace utils

#endif // SRC_THAMESLIB_UTILS_H_
