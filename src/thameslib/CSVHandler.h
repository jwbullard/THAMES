/**
@file CSVHandler.h
@brief Declaration of a class for handling CSV file reading and writing.
*/

#ifndef SRC_THAMESLIB_CSVHANDLER_H_
#define SRC_THAMESLIB_CSVHANDLER_H_

#include "global.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

/**
@class Declare the CSVRow class

This class was taken from an answer at stackoverflow.com:
https://stackoverflow.com/questions/1120140/how-can-i-read-and-parse-csv-files-in-c
*/
class CSVRow {
public:
  std::string_view operator[](std::size_t index) const {
    return std::string_view(&m_line[m_data[index] + 1],
                            m_data[index + 1] - (m_data[index] + 1));
  }
  std::size_t size() const { return m_data.size() - 1; }
  void readNextRow(std::istream &str) {
    std::getline(str, m_line);

    m_data.clear();
    m_data.emplace_back(-1);
    std::string::size_type pos = 0;
    while ((pos = m_line.find(',', pos)) != std::string::npos) {
      m_data.emplace_back(pos);
      ++pos;
    }
    // This checks for a trailing comma with no data after it.
    pos = m_line.size();
    m_data.emplace_back(pos);
  }

private:
  std::string m_line;
  std::vector<int> m_data;
};

std::istream &operator>>(std::istream &str, CSVRow &data) {
  data.readNextRow(str);
  return str;
}

/**
@class Declare the CSVIterator class

This class was taken from an answer at stackoverflow.com:
https://stackoverflow.com/questions/1120140/how-can-i-read-and-parse-csv-files-in-c
*/
class CSVIterator {
public:
  typedef std::input_iterator_tag iterator_category;
  typedef CSVRow value_type;
  typedef std::size_t difference_type;
  typedef CSVRow *pointer;
  typedef CSVRow &reference;

  CSVIterator(std::istream &str) : m_str(str.good() ? &str : nullptr) {
    ++(*this);
  }
  CSVIterator() : m_str(nullptr) {}

  // Pre Increment
  CSVIterator &operator++() {
    if (m_str) {
      if (!((*m_str) >> m_row)) {
        m_str = nullptr;
      }
    }
    return *this;
  }
  // Post increment
  CSVIterator operator++(int) {
    CSVIterator tmp(*this);
    ++(*this);
    return tmp;
  }
  CSVRow const &operator*() const { return m_row; }
  CSVRow const *operator->() const { return &m_row; }

  bool operator==(CSVIterator const &rhs) {
    return ((this == &rhs) ||
            ((this->m_str == nullptr) && (rhs.m_str == nullptr)));
  }
  bool operator!=(CSVIterator const &rhs) { return !((*this) == rhs); }

private:
  std::istream *m_str;
  CSVRow m_row;
};

/**
@class Declare the CSVRange class

This class was taken from an answer at stackoverflow.com:
https://stackoverflow.com/questions/1120140/how-can-i-read-and-parse-csv-files-in-c
*/
class CSVRange {
  std::istream &stream;

public:
  CSVRange(std::istream &str) : stream(str) {}
  CSVIterator begin() const { return CSVIterator{stream}; }
  CSVIterator end() const { return CSVIterator{}; }
};

/// The commented code below shows some ways to implement these classes to read
/// CSV Files

/// Example 1: Using just the CSVRow class

/// int main()
/// {
///     std::ifstream       file("plop.csv");
///
///     CSVRow              row;
///     while(file >> row)
///     {
///         std::cout << "4th Element(" << row[3] << ")\n";
///     }
/// }
///
/// Example 2: Using the CSVIterator class
/// int main()
/// {
///     std::ifstream       file("plop.csv");
///
///     for(CSVIterator loop(file); loop != CSVIterator(); ++loop)
///     {
///         std::cout << "4th Element(" << (*loop)[3] << ")\n";
///     }
/// }
///
/// Example 3: Using the CSVRange class
///
/// int main()
/// {
///     std::ifstream       file("plop.csv");
///
///     for(auto& row: CSVRange(file))
///     {
///         std::cout << "4th Element(" << row[3] << ")\n";
///     }
/// }

#endif // SRC_THAMESLIB_CSVHANDLER_H_
