/**
@file utils.h
@brief Define some simple utility functions.
*/
#ifndef SRC_THAMESLIB_UTILS_H_
#define SRC_THAMESLIB_UTILS_H_
#include "global.h"
#include <sstream>
#include <string>

using namespace std;

/**
@brief Convert an STL string into a given data type.

@param t is the new data type variable that will hold the value
@param s is the string to convert
@return true if the conversion was successful, false otherwise
*/
template <class T> bool from_string(T &t, const string &s) {
  istringstream iss(s, istringstream::in);
  return !(iss >> t).fail();
}

/**
@brief Convert any data type to a string.

@param t is the input data
@return the string that was created to hold the data
*/
template <class T> string to_string(const T &t) {
  ostringstream oss;
  oss << t;
  return oss.str();
}

///
/// The methods below are NOT USED.
///

namespace utils {

void replace(string &where, const string &what, const string &by);

bool start_with(const string &str, const string &what);
bool end_with(const string &str, const string &what);

} // namespace utils

#endif // SRC_THAMESLIB_UTILS_H_
