#include <gtest/gtest.h>
#include "../../Examples/SOCKnapsackInstance/SOCKnapsackProblem.h"

#include <filesystem>
#include <fstream>
#include <string>

using namespace std;
namespace fs = std::filesystem;

class SOCKnapsackProblemTest : public ::testing::Test {
protected:
    /**
     * @brief Writes a two-variable, one-constraint instance and loads it.
     */
    SOCKnapsackInstance* make_instance(const string& linear_weights, int omega) {
        fs::path file_path = fs::temp_directory_path() / "sock_monotone_test_instance.txt";
        ofstream file(file_path);
        file << "2 1\n" << omega << "\n1 1\n10\n" << linear_weights << "\n1 1\n";
        file.close();
        return new SOCKnapsackInstance(file_path.string());
    }
};

TEST_F(SOCKnapsackProblemTest, TestRequiresMonotoneConstraint) {
    SOCKnapsackInstance* negative_weight = make_instance("3 -1", 1);
    ASSERT_THROW(SOCKnapsackProblem(new vector<double>(*negative_weight->initial_state), *negative_weight, 0), invalid_argument);
    delete negative_weight;

    SOCKnapsackInstance* negative_omega = make_instance("3 1", -1);
    ASSERT_THROW(SOCKnapsackProblem(new vector<double>(*negative_omega->initial_state), *negative_omega, 0), invalid_argument);
    delete negative_omega;

    SOCKnapsackInstance* valid = make_instance("3 0", 1);
    ASSERT_NO_THROW(SOCKnapsackProblem(new vector<double>(*valid->initial_state), *valid, 0));
    delete valid;
}
